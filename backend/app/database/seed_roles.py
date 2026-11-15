from sqlalchemy import select

from app.database.connection import SessionLocal
from app.models import Role

ROLES = [
    "EMPLOYEE",
    "DEPARTMENT_ADMIN",
    "SUPER_ADMIN"
]


def seed_roles():
    with SessionLocal() as db:
        try:
            for role_name in ROLES:
                existing_role = db.scalar(
                    select(Role).where(Role.name == role_name)
                )

                if existing_role is None:
                    db.add(Role(name=role_name))
                    print(f"Added: {role_name}")
                else:
                    print(f"Already exists: {role_name}")

            db.commit()
            print("Role seeding completed!")

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    seed_roles()