import httpx
from datetime import datetime
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class EskizSMSService:
    _token: str | None = None
    _token_expires_at: datetime | None = None

    async def _get_token(self) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://notify.eskiz.uz/api/auth/login",
                data={"email": settings.ESKIZ_EMAIL, "password": settings.ESKIZ_PASSWORD}
            )
            response.raise_for_status()
            data = response.json()
            self._token = data["data"]["token"]
            return self._token

    async def _refresh_token(self) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                "https://notify.eskiz.uz/api/auth/refresh",
                headers={"Authorization": f"Bearer {self._token}"}
            )
            response.raise_for_status()
            data = response.json()
            self._token = data["data"]["token"]
            return self._token

    async def _ensure_token(self) -> str:
        if not self._token:
            return await self._get_token()
        return self._token

    async def send_otp(self, phone: str, code: str) -> bool:
        if settings.DEBUG:
            logger.info(f"DEBUG MOCK: OTP code {code} generated for {phone}")
            print(f"DEBUG MOCK: OTP code {code} generated for {phone}")
            return True

        token = await self._ensure_token()
        clean_phone = phone.lstrip('+')

        payload = {
            "mobile_phone": clean_phone,
            "message": f"{settings.APP_NAME}: Your code is {code}. Valid for {settings.OTP_EXPIRE_MINUTES} minutes.",
            "from": settings.ESKIZ_SENDER,
            "callback_url": ""
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://notify.eskiz.uz/api/message/sms/send",
                    headers={"Authorization": f"Bearer {token}"},
                    data=payload
                )
                
                if response.status_code == 401:
                    token = await self._refresh_token()
                    response = await client.post(
                        "https://notify.eskiz.uz/api/message/sms/send",
                        headers={"Authorization": f"Bearer {token}"},
                        data=payload
                    )

                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Failed to send SMS to {phone}: {e}")
                return False

eskiz_service = EskizSMSService()
