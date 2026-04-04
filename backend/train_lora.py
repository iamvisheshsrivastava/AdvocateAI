#!/usr/bin/env python
# pyright: reportMissingImports=false

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch
from datasets import Dataset, load_dataset
from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)


DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
DEFAULT_TARGET_MODULES = "q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj"


@dataclass(frozen=True)
class TrainingManifest:
    base_model: str
    dataset_path: str
    output_dir: str
    use_qlora: bool
    max_length: int
    validation_split: float
    train_rows: int
    eval_rows: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One-time LoRA/QLoRA fine-tuning script for AdvocateAI."
    )
    parser.add_argument("--dataset", required=True, help="Path to a JSON or JSONL dataset file.")
    parser.add_argument("--output-dir", default="artifacts/lora_adapter", help="Directory for the adapter and training artifacts.")
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL, help="Hugging Face causal LM to fine-tune.")
    parser.add_argument("--max-length", type=int, default=2048, help="Maximum token length for each training example.")
    parser.add_argument("--validation-split", type=float, default=0.05, help="Fraction of rows reserved for evaluation.")
    parser.add_argument("--epochs", type=float, default=1.0, help="Number of training epochs.")
    parser.add_argument("--train-batch-size", type=int, default=1, help="Per-device training batch size.")
    parser.add_argument("--eval-batch-size", type=int, default=1, help="Per-device evaluation batch size.")
    parser.add_argument("--gradient-accumulation-steps", type=int, default=16, help="Gradient accumulation steps.")
    parser.add_argument("--learning-rate", type=float, default=2e-4, help="Learning rate for adapter training.")
    parser.add_argument("--warmup-ratio", type=float, default=0.03, help="Warmup ratio for the scheduler.")
    parser.add_argument("--logging-steps", type=int, default=10, help="Log every N steps.")
    parser.add_argument("--save-steps", type=int, default=100, help="Save every N steps.")
    parser.add_argument("--eval-steps", type=int, default=100, help="Evaluate every N steps when an eval split exists.")
    parser.add_argument("--save-total-limit", type=int, default=2, help="How many checkpoints to keep.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank.")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha.")
    parser.add_argument("--lora-dropout", type=float, default=0.05, help="LoRA dropout.")
    parser.add_argument("--target-modules", default=DEFAULT_TARGET_MODULES, help="Comma-separated module names to adapt.")
    parser.add_argument("--trust-remote-code", action="store_true", help="Allow custom model code from Hugging Face.")
    parser.add_argument("--report-to", default="none", help="Trainer reporting target, for example none, tensorboard, or wandb.")
    parser.add_argument("--no-qlora", dest="use_qlora", action="store_false", help="Train with regular LoRA instead of 4-bit QLoRA.")
    parser.set_defaults(use_qlora=True)
    return parser.parse_args()


def load_training_dataset(dataset_path: Path) -> Dataset:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    raw_dataset = load_dataset("json", data_files=str(dataset_path), split="train")
    if len(raw_dataset) == 0:
        raise ValueError("Dataset is empty.")
    return raw_dataset


def split_dataset(dataset: Dataset, validation_split: float, seed: int) -> tuple[Dataset, Dataset | None]:
    if validation_split <= 0.0 or len(dataset) < 2:
        return dataset, None

    eval_fraction = min(validation_split, 0.5)
    eval_rows = max(1, int(len(dataset) * eval_fraction))
    if eval_rows >= len(dataset):
        eval_rows = len(dataset) - 1

    split = dataset.train_test_split(test_size=eval_rows, seed=seed, shuffle=True)
    return split["train"], split["test"]


def _message_to_dict(item: Any) -> dict[str, str] | None:
    if not isinstance(item, dict):
        return None

    role = str(item.get("role") or "user").strip()
    content = str(item.get("content") or "").strip()
    if not content:
        return None

    return {"role": role, "content": content}


def _render_messages_example(messages: list[Any], tokenizer: AutoTokenizer) -> str | None:
    normalized_messages = [item for item in (_message_to_dict(message) for message in messages) if item]
    if not normalized_messages:
        return None

    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(  # type: ignore[no-any-return]
            normalized_messages,
            tokenize=False,
            add_generation_prompt=False,
        )

    return "\n".join(f"{message['role'].upper()}: {message['content']}" for message in normalized_messages)


def _render_prompt_response_example(example: dict[str, Any]) -> str | None:
    prompt = str(example.get("prompt") or "").strip()
    response = str(example.get("response") or example.get("output") or example.get("answer") or "").strip()
    if prompt and response:
        return f"### Prompt\n{prompt}\n\n### Response\n{response}"
    return None


def _render_instruction_example(example: dict[str, Any]) -> str | None:
    instruction = str(example.get("instruction") or "").strip()
    response = str(example.get("response") or example.get("output") or example.get("answer") or "").strip()
    input_text = str(example.get("input") or example.get("context") or "").strip()
    text = str(example.get("text") or "").strip()

    if not instruction and not response and not text:
        return None

    parts = ["### Instruction", instruction or text or ""]
    if input_text:
        parts.extend(["### Input", input_text])
    parts.extend(["### Response", response or text or ""])
    return "\n\n".join(parts).strip()


def render_example(example: dict[str, Any], tokenizer: AutoTokenizer) -> str:
    messages = example.get("messages")
    if isinstance(messages, list) and messages:
        rendered_messages = _render_messages_example(messages, tokenizer)
        if rendered_messages:
            return rendered_messages

    prompt_response = _render_prompt_response_example(example)
    if prompt_response:
        return prompt_response

    instruction_example = _render_instruction_example(example)
    if instruction_example:
        return instruction_example

    raise ValueError("Each record needs messages, prompt/response, instruction/output, or text fields.")


def tokenize_dataset(dataset: Dataset, tokenizer: AutoTokenizer, max_length: int) -> Dataset:
    def _tokenize(example: dict[str, Any]) -> dict[str, Any]:
        text = render_example(example, tokenizer)
        tokenized = tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            padding=False,
        )
        return tokenized

    return dataset.map(_tokenize, remove_columns=dataset.column_names)


def build_model(tokenizer: AutoTokenizer, base_model: str, use_qlora: bool, trust_remote_code: bool) -> AutoModelForCausalLM:
    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    quantization_config = None

    if use_qlora:
        if not torch.cuda.is_available():
            raise RuntimeError("QLoRA requires a CUDA-capable GPU.")

        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        quantization_config=quantization_config,
        trust_remote_code=trust_remote_code,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token or tokenizer.unk_token

    model.config.pad_token_id = tokenizer.pad_token_id
    model.config.use_cache = False

    if use_qlora:
        model = prepare_model_for_kbit_training(model)

    return model


def build_collator(tokenizer: AutoTokenizer):
    def _collate(features: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        batch = tokenizer.pad(features, return_tensors="pt")
        labels = batch["input_ids"].clone()
        labels[batch["attention_mask"] == 0] = -100
        batch["labels"] = labels
        return batch

    return _collate


def main() -> int:
    args = parse_args()
    dataset_path = Path(args.dataset).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    adapter_dir = output_dir / "adapter"
    checkpoints_dir = output_dir / "checkpoints"
    output_dir.mkdir(parents=True, exist_ok=True)
    adapter_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(
        args.base_model,
        use_fast=True,
        trust_remote_code=args.trust_remote_code,
    )

    raw_dataset = load_training_dataset(dataset_path)
    train_dataset, eval_dataset = split_dataset(raw_dataset, args.validation_split, args.seed)

    tokenized_train = tokenize_dataset(train_dataset, tokenizer, args.max_length)
    tokenized_eval = tokenize_dataset(eval_dataset, tokenizer, args.max_length) if eval_dataset is not None else None

    model = build_model(tokenizer, args.base_model, args.use_qlora, args.trust_remote_code)
    target_modules = [module.strip() for module in args.target_modules.split(",") if module.strip()]

    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        target_modules=target_modules,
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    training_args = TrainingArguments(
        output_dir=str(checkpoints_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.train_batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        warmup_ratio=args.warmup_ratio,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        save_total_limit=args.save_total_limit,
        evaluation_strategy="steps" if tokenized_eval is not None else "no",
        save_strategy="steps",
        load_best_model_at_end=tokenized_eval is not None,
        fp16=torch.cuda.is_available() and not use_bf16,
        bf16=use_bf16,
        optim="paged_adamw_8bit" if args.use_qlora else "adamw_torch",
        report_to=args.report_to,
        remove_unused_columns=False,
        seed=args.seed,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_eval,
        data_collator=build_collator(tokenizer),
        tokenizer=tokenizer,
    )

    train_result = trainer.train()
    metrics = dict(train_result.metrics)
    if tokenized_eval is not None:
        metrics.update(trainer.evaluate())

    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))

    manifest = TrainingManifest(
        base_model=args.base_model,
        dataset_path=str(dataset_path),
        output_dir=str(output_dir),
        use_qlora=bool(args.use_qlora),
        max_length=args.max_length,
        validation_split=args.validation_split,
        train_rows=len(train_dataset),
        eval_rows=len(eval_dataset) if eval_dataset is not None else 0,
    )
    (output_dir / "training_manifest.json").write_text(
        json.dumps(
            {
                "manifest": asdict(manifest),
                "metrics": metrics,
                "training_args": {
                    "epochs": args.epochs,
                    "train_batch_size": args.train_batch_size,
                    "eval_batch_size": args.eval_batch_size,
                    "gradient_accumulation_steps": args.gradient_accumulation_steps,
                    "learning_rate": args.learning_rate,
                    "warmup_ratio": args.warmup_ratio,
                    "logging_steps": args.logging_steps,
                    "save_steps": args.save_steps,
                    "eval_steps": args.eval_steps,
                    "save_total_limit": args.save_total_limit,
                    "lora_r": args.lora_r,
                    "lora_alpha": args.lora_alpha,
                    "lora_dropout": args.lora_dropout,
                    "target_modules": target_modules,
                    "use_qlora": args.use_qlora,
                    "max_length": args.max_length,
                },
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    print(f"Adapter saved to: {adapter_dir}")
    print(f"Training manifest saved to: {output_dir / 'training_manifest.json'}")
    if tokenized_eval is not None:
        print(f"Evaluation metrics: {metrics}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())