"""Migrations SQLite idempotentes, exécutées à chaque démarrage après create_all.

Pas d'alembic dans ce projet : chaque migration doit pouvoir tourner plusieurs
fois sans effet de bord (garde PRAGMA / NOT EXISTS).
"""
import uuid

from loguru import logger
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Labels historiques des BU — utilisés uniquement pour le backfill des comptes
# LinkedIn créés avant l'existence de la table accounts.
BU_LABELS = {"noisyless": "Noisyless", "afluxo": "Afluxo", "mbhrep": "MBHREP"}


def run_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        _add_posts_account_id(conn)
        _backfill_accounts_from_personas(conn)


def _add_posts_account_id(conn) -> None:
    cols = [row[1] for row in conn.execute(text("PRAGMA table_info(posts)"))]
    if "account_id" not in cols:
        conn.execute(text("ALTER TABLE posts ADD COLUMN account_id TEXT REFERENCES accounts(id) ON DELETE SET NULL"))
        logger.info("Migration: posts.account_id added")


def _backfill_accounts_from_personas(conn) -> None:
    personas = conn.execute(text(
        "SELECT id, bu, linkedin_page_url, instagram_page_url FROM personas "
        "WHERE linkedin_page_url IS NOT NULL OR instagram_page_url IS NOT NULL"
    )).fetchall()

    created = 0
    for pid, bu, li_url, ig_url in personas:
        if li_url:
            created += _insert_account_if_missing(
                conn, pid, "linkedin", "company_page", li_url,
                BU_LABELS.get(bu, bu),
            )
        if ig_url:
            created += _insert_account_if_missing(
                conn, pid, "instagram", "business_account", ig_url,
                _handle_from_url(ig_url),
            )
    if created:
        logger.info(f"Migration: {created} account(s) backfilled from persona page URLs")


def _insert_account_if_missing(conn, persona_id, platform, kind, page_url, identity_name) -> int:
    exists = conn.execute(text(
        "SELECT 1 FROM accounts WHERE persona_id = :pid AND platform = :platform LIMIT 1"
    ), {"pid": persona_id, "platform": platform}).first()
    if exists:
        return 0
    conn.execute(text(
        "INSERT INTO accounts (id, persona_id, platform, kind, page_url, identity_name, enabled, created_at, updated_at) "
        "VALUES (:id, :pid, :platform, :kind, :page_url, :identity_name, 1, datetime('now'), datetime('now'))"
    ), {
        "id": str(uuid.uuid4()),
        "pid": persona_id,
        "platform": platform,
        "kind": kind,
        "page_url": page_url,
        "identity_name": identity_name,
    })
    return 1


def _handle_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1].split("?")[0]
