from app.core.db import get_db
from .domain import User


class UsersDAO:

    @staticmethod
    def _get_guide_language_ids(guide_id: str):
        db = get_db()

        rows = db.execute(
            """
            SELECT language_id
            FROM guide_languages
            WHERE guide_id = ?
            """,
            (guide_id,)
        ).fetchall()

        return [row["language_id"] for row in rows]

    @staticmethod
    def _attach_guide_languages(user: User):
        if user is None:
            return None

        if user.role == "guide":
            user.guide_language_ids = UsersDAO._get_guide_language_ids(user.id)

        return user

    @staticmethod
    def get_user_by_id(user_id: str):
        db = get_db()

        row = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

        user = User.from_row(row)
        return UsersDAO._attach_guide_languages(user)

    @staticmethod
    def get_user_by_email(email: str):
        db = get_db()

        row = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        user = User.from_row(row)
        return UsersDAO._attach_guide_languages(user)

    @staticmethod
    def get_user_by_username(username: str):
        db = get_db()

        row = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        user = User.from_row(row)
        return UsersDAO._attach_guide_languages(user)

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

            if user.role == "guide":
                for language_id in user.guide_language_ids:
                    db.execute(
                        """
                        INSERT INTO guide_languages
                        (guide_id, language_id, created_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        """,
                        (
                            user.id,
                            language_id
                        )
                    )

            db.commit()
            return True

        except Exception as e:
            print(f"DB error during registration: {e}")
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
            print(f"DB error while updating user: {e}")
            db.rollback()
            return False

    @staticmethod
    def replace_guide_languages(guide_id: str, language_ids: list[int]) -> bool:
        db = get_db()

        try:
            db.execute(
                "DELETE FROM guide_languages WHERE guide_id = ?",
                (guide_id,)
            )

            for language_id in language_ids:
                db.execute(
                    """
                    INSERT INTO guide_languages
                    (guide_id, language_id, created_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        guide_id,
                        language_id
                    )
                )

            db.commit()
            return True

        except Exception as e:
            print(f"DB error while updating guide languages: {e}")
            db.rollback()
            return False
        
    @staticmethod
    def replace_guide_languages(guide_id: str, language_ids: list[int]) -> bool:
        db = get_db()

        try:
            db.execute(
                "DELETE FROM guide_languages WHERE guide_id = ?",
                (guide_id,)
            )

            for language_id in language_ids:
                db.execute(
                    """
                    INSERT INTO guide_languages
                    (guide_id, language_id, created_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        guide_id,
                        language_id
                    )
                )

            db.commit()
            return True

        except Exception as e:
            print(f"DB error while updating guide languages: {e}")
            db.rollback()
            return False
        
    @staticmethod
    def list_users_by_role(role: str):
        db = get_db()

        rows = db.execute(
            """
            SELECT *
            FROM users
            WHERE role = ?
            ORDER BY last_name ASC, first_name ASC, email ASC
            """,
            (role,)
        ).fetchall()

        return [User.from_row(row) for row in rows]


    @staticmethod
    def count_users_by_role(role: str):
        db = get_db()

        row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM users
            WHERE role = ?
            """,
            (role,)
        ).fetchone()

        return int(row["total"])
            
