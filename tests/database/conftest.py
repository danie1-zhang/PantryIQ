from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(autouse=True)
def isolated_database(clean_test_database: None) -> Generator[None, None, None]:
    yield


@pytest.fixture
def db_session(test_session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with test_session_factory() as session:
        yield session
