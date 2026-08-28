"""Email via Resend; dev/test tanpa API key → log link ke console.

Adapter: semua pemanggilan email lewat sini — provider bisa diganti tanpa
mengubah logika (BLUEPRINT §21).
"""
import logging

import httpx

from packages.config import get_settings

logger = logging.getLogger("api.email")


def send_email(to: str, subject: str, html: str, text: str = "") -> bool:
    settings = get_settings()
    if settings.resend_api_key:
        try:
            resp = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": "MT5 Journal <noreply@mt5journal.app>",
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "text": text,
                },
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("resend gagal: %s", exc)
            return False
    # Dev/test fallback: email "dikirim" = ditulis ke log
    logger.info("EMAIL(dev) to=%s subject=%s\n%s", to, subject, html)
    return True
