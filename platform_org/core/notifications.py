import os
import json
import requests
from django.conf import settings
from django.core.mail import send_mail

def send_teams_webhook(message: str):
    url = getattr(settings, "TEAMS_WEBHOOK_URL", None) or os.getenv("TEAMS_WEBHOOK_URL")
    if not url:
        return False
    payload = {"text": message}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code >= 200 and r.status_code < 300
    except Exception:
        return False

def send_alert_email(subject: str, message: str, to_emails: list[str]):
    if not to_emails:
        return False
    try:
        send_mail(subject, message, getattr(settings, "DEFAULT_FROM_EMAIL", None), to_emails, fail_silently=True)
        return True
    except Exception:
        return False
