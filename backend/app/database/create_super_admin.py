import os

from dotenv import load_dotenv
from sqlalchemy import select

from app.database.connection import SessionLocal
from app.models import User, Role
from app.security.password import hash_password


load_dotenv()

ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL")
ADMIN_NAME = os.getenv("SUPER_ADMIN_NAME")
ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD")


def create_super_admin():

    if not all([ADMIN_EMAIL, ADMIN_NAME, ADMIN_PASSWORD]):
        raise ValueError(
            "Super Admin configuration is missing from .env"
        )

    email = ADMIN_EMAIL.lower()

    with SessionLocal() as db:
        try:
            admin_role = db.scalar(
                select(Role).where(Role.name == "SUPER_ADMIN")
            )

            if admin_role is None:
                raise ValueError(
                    "SUPER_ADMIN role not found. Run seed_roles first."
                )

            user = db.scalar(
                select(User).where(User.email == email)
            )

            if user is None:
                user = User(
                    email=email,
                    full_name=ADMIN_NAME,
                    password_hash=hash_password(ADMIN_PASSWORD)
                )

                db.add(user)
                db.flush()

                print("Super Admin user created.")

            if admin_role not in user.roles:
                user.roles.append(admin_role)
                print("SUPER_ADMIN role assigned.")
            else:
                print("SUPER_ADMIN role already assigned.")

            db.commit()
            print("Super Admin setup completed!")

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    create_super_admin()