"""Email via Resend; dev/test tanpa API key → log link ke console.

Adapter: semua pemanggilan email lewat sini — provider bisa diganti tanpa
mengubah logika (BLUEPRINT §21).
"""
import logging

import httpx

from packages.config import get_settings

logger = logging.getLogger("api.email")


def send_email(
    to: str,
    subject: str,
    html: str,
    text: str = "",
    attachment: tuple[str, bytes, str] | None = None,
) -> bool:
    """Kirim email; attachment = (filename, bytes, mime). Dev → log console."""
    settings = get_settings()
    if settings.resend_api_key:
        try:
            payload: dict = {
                "from": "MT5 Journal <noreply@mt5journal.app>",
                "to": [to],
                "subject": subject,
                "html": html,
                "text": text,
            }
            if attachment is not None:
                import base64

                fname, content, mime = attachment
                payload["attachments"] = [
                    {
                        "filename": fname,
                        "content": base64.b64encode(content).decode(),
                        "content_type": mime,
                    }
                ]
            resp = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json=payload,
                timeout=20,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("resend gagal: %s", exc)
            return False
    # Dev/test fallback: email "dikirim" = ditulis ke log
    if attachment is not None:
        logger.info(
            "EMAIL(dev) to=%s subject=%s attachment=%s (%d bytes)\n%s",
            to, subject, attachment[0], len(attachment[1]), html,
        )
    else:
        logger.info("EMAIL(dev) to=%s subject=%s\n%s", to, subject, html)
    return True
