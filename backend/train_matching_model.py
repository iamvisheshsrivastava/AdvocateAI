#!/usr/bin/env python

import json

from services.ml_matching_service import train_lawyer_match_model


if __name__ == "__main__":
    manifest = train_lawyer_match_model()
    print(json.dumps(manifest, indent=2, ensure_ascii=True))
