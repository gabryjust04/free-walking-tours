import os
import smtplib
from email.message import EmailMessage


def send_plain_email(to_email: str, subject: str, body: str):
    smtp_host = os.environ.get("MAIL_HOST")
    smtp_port = int(os.environ.get("MAIL_PORT", "587"))
    smtp_username = os.environ.get("MAIL_USERNAME")
    smtp_password = os.environ.get("MAIL_PASSWORD")
    mail_from = os.environ.get("MAIL_FROM", smtp_username)

    if not smtp_host or not smtp_username or not smtp_password or not mail_from:
        raise RuntimeError("Missing mail configuration.")

    message = EmailMessage()
    message["From"] = mail_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(message)