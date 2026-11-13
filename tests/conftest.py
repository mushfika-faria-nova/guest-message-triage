import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from guest_message_triage.db import Base

# A separate database, so tests never touch dev data. CI can point this elsewhere.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://triage:triage@localhost:5432/triage_test"
)


# scope="session": created once per test run, not per test.
@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


# A fresh session per test; tables emptied afterwards so tests don't see each other's rows.
@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE messages, tickets RESTART IDENTITY"))
