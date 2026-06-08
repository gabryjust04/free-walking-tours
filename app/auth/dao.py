from app.core.db import get_db
from .domain import User


class UsersDAO:

    @staticmethod
    def get_user_by_id(user_id: str):
        db = get_db()

        row = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

        return User.from_row(row)

    @staticmethod
    def get_user_by_email(email: str):
        db = get_db()

        row = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        return User.from_row(row)

    @staticmethod
    def get_user_by_username(username: str):
        db = get_db()

        row = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        return User.from_row(row)

    @staticmethod
    def add_user(user: User) -> bool:
        db = get_db()

        try:
            db.execute(
                """
                INSERT INTO users 
                (id, email, password_hash, first_name, last_name, username, role, profile_photo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user.id,
                    user.email,
                    user.password_hash,
                    user.first_name,
                    user.last_name,
                    user.username,
                    user.role,
                    user.profile_photo
                )
            )

            db.commit()
            return True

        except Exception as e:
            print(f"Errore DB durante registrazione: {e}")
            db.rollback()
            return False

    @staticmethod
    def update_user(user: User) -> bool:
        db = get_db()

        try:
            db.execute(
                """
                UPDATE users
                SET email = ?,
                    password_hash = ?,
                    first_name = ?,
                    last_name = ?,
                    username = ?,
                    role = ?,
                    profile_photo = ?
                WHERE id = ?
                """,
                (
                    user.email,
                    user.password_hash,
                    user.first_name,
                    user.last_name,
                    user.username,
                    user.role,
                    user.profile_photo,
                    user.id
                )
            )

            db.commit()
            return True

        except Exception as e:
            print(f"Errore DB durante aggiornamento utente: {e}")
            db.rollback()
            return False