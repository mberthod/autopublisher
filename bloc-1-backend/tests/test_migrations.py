from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.migrations import run_migrations
from app.models import Base, Persona


def _make_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'migr.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def _seed_legacy_persona(engine):
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Persona(
        id="p_legacy", bu="noisyless", nom="Legacy", besoins="b", frustrations="f",
        cible="c", charte_branding={},
        linkedin_page_url="https://www.linkedin.com/company/noisyless/admin/",
        instagram_page_url="https://www.instagram.com/noisyless/",
    ))
    db.commit()
    db.close()


def test_backfill_creates_accounts(tmp_path):
    engine = _make_engine(tmp_path)
    _seed_legacy_persona(engine)
    run_migrations(engine)

    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT platform, kind, page_url, identity_name FROM accounts WHERE persona_id = 'p_legacy' ORDER BY platform"
        )).fetchall()
    assert len(rows) == 2
    ig, li = rows[0], rows[1]
    assert ig == ("instagram", "business_account", "https://www.instagram.com/noisyless/", "noisyless")
    assert li == ("linkedin", "company_page", "https://www.linkedin.com/company/noisyless/admin/", "Noisyless")


def test_migrations_are_idempotent(tmp_path):
    engine = _make_engine(tmp_path)
    _seed_legacy_persona(engine)
    run_migrations(engine)
    run_migrations(engine)

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM accounts WHERE persona_id = 'p_legacy'")).scalar()
    assert count == 2


def test_posts_account_id_column_added(tmp_path):
    # Simule une vieille base : table posts sans account_id
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}", connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE personas (id TEXT PRIMARY KEY, bu TEXT, linkedin_page_url TEXT, instagram_page_url TEXT)"))
        conn.execute(text("CREATE TABLE accounts (id TEXT PRIMARY KEY, persona_id TEXT, platform TEXT, kind TEXT, page_url TEXT, identity_name TEXT, asset_id TEXT, enabled INTEGER, created_at TEXT, updated_at TEXT)"))
        conn.execute(text("CREATE TABLE posts (id TEXT PRIMARY KEY, platform TEXT)"))

    run_migrations(engine)
    run_migrations(engine)  # idempotent

    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(posts)"))]
    assert "account_id" in cols
