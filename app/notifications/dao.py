import uuid

from app.core.db import get_db


class EmailQueueDAO:

    @staticmethod
    def enqueue_email(
        recipient_email: str,
        subject: str,
        body: str,
        email_type: str,
        send_at: str,
        reservation_id: str | None = None,
    ):
        db = get_db()

        email_id = str(uuid.uuid4())

        db.execute(
            """
            INSERT INTO email_queue
            (
                id,
                recipient_email,
                subject,
                body,
                email_type,
                reservation_id,
                send_at,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                email_id,
                recipient_email,
                subject,
                body,
                email_type,
                reservation_id,
                send_at,
            )
        )

        return email_id

    @staticmethod
    def list_due_pending_emails(now_value: str, limit: int = 20):
        db = get_db()

        rows = db.execute(
            """
            SELECT *
            FROM email_queue
            WHERE status = 'pending'
              AND send_at <= ?
            ORDER BY send_at ASC
            LIMIT ?
            """,
            (now_value, limit)
        ).fetchall()

        return rows

    @staticmethod
    def mark_email_as_sent(email_id: str, sent_at: str):
        db = get_db()

        db.execute(
            """
            UPDATE email_queue
            SET status = 'sent',
                sent_at = ?,
                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (sent_at, email_id)
        )

        db.commit()

    @staticmethod
    def mark_email_as_failed(email_id: str, error_message: str):
        db = get_db()

        db.execute(
            """
            UPDATE email_queue
            SET status = 'failed',
                error_message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (error_message, email_id)
        )

        db.commit()

    @staticmethod
    def cancel_pending_emails_by_reservation(reservation_id: str):
        db = get_db()

        cursor = db.execute(
            """
            UPDATE email_queue
            SET status = 'cancelled',
                updated_at = CURRENT_TIMESTAMP
            WHERE reservation_id = ?
              AND status = 'pending'
            """,
            (reservation_id,)
        )

        return cursor.rowcount
