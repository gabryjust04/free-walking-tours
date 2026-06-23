from app import create_app
from app.core.utils import get_now_in_app_timezone
from app.notifications.dao import EmailQueueDAO
from app.notifications.mailer import send_plain_email


def format_now():
    return get_now_in_app_timezone().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")


def send_pending_emails():
    now_value = format_now()

    emails = EmailQueueDAO.list_due_pending_emails(
        now_value=now_value,
        limit=20,
    )

    for email in emails:
        try:
            send_plain_email(
                to_email=email["recipient_email"],
                subject=email["subject"],
                body=email["body"],
            )

            EmailQueueDAO.mark_email_as_sent(
                email_id=email["id"],
                sent_at=format_now(),
            )

            print(f"Sent email {email['id']} to {email['recipient_email']}")

        except Exception as e:
            EmailQueueDAO.mark_email_as_failed(
                email_id=email["id"],
                error_message=str(e),
            )

            print(f"Failed email {email['id']}: {e}")


if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        send_pending_emails()