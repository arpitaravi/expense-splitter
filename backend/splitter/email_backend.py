"""Email over HTTPS (Brevo API). Works on hosts that block SMTP ports (e.g. Render free tier)."""
import json
import logging
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class BrevoEmailBackend(BaseEmailBackend):
    url = "https://api.brevo.com/v3/smtp/email"

    def send_messages(self, email_messages):
        sent = 0
        for m in email_messages:
            name, addr = parseaddr(m.from_email or settings.DEFAULT_FROM_EMAIL)
            payload = {
                "sender": {"email": addr, "name": name or "Splitter"},
                "to": [{"email": r} for r in m.to],
                "subject": m.subject,
                "textContent": m.body,
            }
            html = next((c for c, t in getattr(m, "alternatives", []) if t == "text/html"), None)
            if html:
                payload["htmlContent"] = html
            req = urllib.request.Request(
                self.url, data=json.dumps(payload).encode(), method="POST",
                headers={"api-key": settings.BREVO_API_KEY, "content-type": "application/json",
                         "accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=10):
                    sent += 1
            except Exception:
                logger.exception("Brevo send failed")
                if not self.fail_silently:
                    raise
        return sent
