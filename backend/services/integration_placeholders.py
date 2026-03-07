class NotificationServicePlaceholder:
    async def send_case_update(self, user_id: int, message: str):
        return {"queued": False, "reason": "Push notifications not integrated yet"}


class PaymentsServicePlaceholder:
    async def create_checkout_session(self, user_id: int, plan: str):
        return {"enabled": False, "reason": "Stripe integration pending"}


class StorageServicePlaceholder:
    async def create_upload_slot(self, user_id: int, filename: str):
        return {"enabled": False, "reason": "Document upload integration pending"}


class MessagingServicePlaceholder:
    async def open_case_channel(self, case_id: int):
        return {"enabled": False, "reason": "Realtime messaging integration pending"}
