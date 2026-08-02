"""Create the temporary local user used before authentication is implemented."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.models import User  # noqa: E402
from src.database.session import SessionLocal  # noqa: E402


def main() -> None:
    with SessionLocal.begin() as session:
        user = session.scalar(select(User).where(User.username == "development_user"))
        if user is None:
            session.add(
                User(
                    email="developer@example.com",
                    username="development_user",
                    password_hash="authentication-not-implemented",
                    name="Development User",
                )
            )
            print("Development user created")
        else:
            print("Development user already exists")


if __name__ == "__main__":
    main()
