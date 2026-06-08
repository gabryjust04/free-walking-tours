from dataclasses import dataclass
from flask_login import UserMixin


@dataclass
class User(UserMixin):
    id: str
    role: str
    email: str
    password_hash: str
    username: str
    first_name: str
    last_name: str
    profile_photo: str = "default.png"

    @staticmethod
    def from_row(row):
        if row is None:
            return None

        profile_photo = "default.png"

        if "profile_photo" in row.keys() and row["profile_photo"] is not None:
            profile_photo = row["profile_photo"]

        return User(
            id=row["id"],
            role=row["role"],
            email=row["email"],
            password_hash=row["password_hash"],
            username=row["username"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            profile_photo=profile_photo
        )