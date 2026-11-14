"""Sending email. With SMTP_HOST set, real SMTP. Otherwise a log mailer: the whole email goes to the server log and to
the Redis list "outbox" (last 50), so it can be read in development and in demos. Nothing is sent."""
import json
import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage

from . import config

log = logging.getLogger("roleshift.mail")


def is_log_mailer() -> bool:
    return not config.SMTP_HOST


def send(r, to: str, subject: str, body: str) -> None:
    """Raises on a real SMTP failure; the caller leaves the reminder unsent so the next run retries."""
    if is_log_mailer():
        log.info("LOG MAILER to=%s subject=%s\n%s", to, subject, body)
        r.lpush("outbox", json.dumps({"to": to, "subject": subject, "body": body, "at": datetime.now(timezone.utc).isoformat()}))
        r.ltrim("outbox", 0, 49)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.SMTP_FROM, to, subject
    msg.set_content(body)
    if config.SMTP_PORT == 465:
        smtp = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=20, context=ssl.create_default_context())
    else:
        smtp = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20)
        smtp.starttls(context=ssl.create_default_context())
    with smtp:
        if config.SMTP_USER:
            smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
        smtp.send_message(msg)
    log.info("email sent subject=%s", subject)  # no address, no content
