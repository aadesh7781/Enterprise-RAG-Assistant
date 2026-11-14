from sqlalchemy import select

from app.database.connection import SessionLocal
from app.models import Department


DEPARTMENTS = ["HR", "Finance", "Engineering"]


def seed_departments():
    with SessionLocal() as db:
        try:
            for department_name in DEPARTMENTS:

                existing_department = db.scalar(
                    select(Department).where(
                        Department.name == department_name
                    )
                )

                if existing_department is None:
                    db.add(Department(name=department_name))
                    print(f"Added: {department_name}")
                else:
                    print(f"Already exists: {department_name}")

            db.commit()
            print("Department seeding completed!")

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    seed_departments()