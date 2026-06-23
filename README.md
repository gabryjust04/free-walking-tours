# Free Walking Tours

## User credentials

| Role | Email / Username | Password |
| --- | --- | --- |
| Admin |  |  |
| Guide |  |  |
| Participant |  |  |

## Testing instructions

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install the project dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with the required environment variables:

```env
SECRET_KEY=
DATABASE_PATH=database/database.db
MAIL_HOST=
MAIL_PORT=587
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_FROM=
```

4. Start the Flask web application:

```bash
flask --app app run --debug
```

5. Open the application in the browser:

```text
http://127.0.0.1:5000
```

6. To process pending email queue records manually, run:

```bash
python app/notifications/send_pending_emails.py
```

## Project structure

- `app/auth`: login, signup, user domain objects, and user DAO.
- `app/public`: public pages, tour listings, booking flow, and reservation cancellation.
- `app/tours`: tour, event, reservation, language, theme domain objects and DAOs.
- `app/guide_dashboard`: guide dashboard routes and helpers.
- `app/admin`: admin routes and helper functions.
- `app/core`: shared Flask setup utilities, database connection, login manager, and formatting helpers.
- `app/notifications`: email queue DAO, SMTP mailer, and script for sending pending emails.
- `app/templates`: Jinja templates.
- `app/static`: CSS, uploaded images, and static assets.
- `database`: SQLite database file.

## Email queue

Emails are not sent directly during a Flask request.

When a participant books a tour, the booking is saved normally in `tour_reservations`. In the same transaction, the application inserts email records into `email_queue`:

- one `booking_confirmation` email with `status = 'pending'` and `send_at` set to the current time;
- one `booking_reminder` email with `status = 'pending'` and `send_at` set to 24 hours before the tour, only if that time is still in the future.

When a reservation is cancelled, pending emails linked to that reservation are marked as `cancelled`.

The script `app/notifications/send_pending_emails.py` sends queued emails whose `status` is `pending` and whose `send_at` is due. After each attempt, it marks the row as `sent` or `failed`. The script waits one second between emails.

## Deployed application URL
