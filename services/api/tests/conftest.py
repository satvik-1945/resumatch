import os

import pytest
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

load_dotenv()
test_url = os.environ.get("TEST_DATABASE_URL")
if not test_url or not (make_url(test_url).database or "").endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL must point to a disposable PostgreSQL DB ending _test")
os.environ["DATABASE_URL"] = test_url
os.environ["WEB_ORIGIN"] = "http://localhost:3000"
os.environ["WEB_ADDITIONAL_ORIGINS"] = '["http://127.0.0.1:3000"]'
os.environ["REGISTRATION_ENABLED"] = "true"
os.environ["COOKIE_SECURE"] = "false"
os.environ["LLM_API_KEY"] = ""

from resumatch.config import get_settings  # noqa: E402
from resumatch.db import get_engine  # noqa: E402
from resumatch.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated():
    get_settings.cache_clear()
    engine = create_engine(test_url)
    with engine.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    command.upgrade(Config("alembic.ini"), "head")
    yield
    engine.dispose()
    get_engine().dispose()


@pytest.fixture(autouse=True)
def clean(migrated):
    with get_engine().begin() as c:
        c.execute(text("TRUNCATE users CASCADE"))


@pytest.fixture
def client():
    with TestClient(app, headers={"origin": "http://localhost:3000"}) as c:
        yield c


@pytest.fixture
def other():
    with TestClient(app, headers={"origin": "http://localhost:3000"}) as c:
        yield c


@pytest.fixture
def db():
    with Session(get_engine()) as s:
        yield s
