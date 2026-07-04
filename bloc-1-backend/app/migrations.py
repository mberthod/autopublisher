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


NOISYLESS_POSITIONING = """NOISYLESS — écosystème de capteurs environnementaux (bruit + qualité d'air + présence) pour locations courte durée et hôtellerie. Sans caméra ni micro. Hébergé en France (RGPD).

CIBLE : propriétaires et gestionnaires de locations courte durée (Airbnb, Booking, villas, appart-hôtels), 1 à 50+ biens, France/Europe. En priorité les biens haut de gamme ou ceux ayant déjà subi un incident (fête, dégâts, plainte de voisinage).

DOULEUR : une fête non détectée = review 1 étoile, dégâts, plainte du voisin, risque de suspension Airbnb. 3 à 8 incidents/an par location, coût 800 à 3000€ (jusqu'à 10 000€ sur une villa premium). Les capteurs classiques ne détectent que le bruit ou le mouvement, pas la présence réelle ni le nombre de personnes.

DIFFÉRENCIATION : contrairement aux solutions qui disent juste « il y a du bruit », Noisyless dit COMBIEN de personnes sont réellement dans le bien, dans QUELLE pièce, et alerte AVANT que le voisin appelle. 3 axes (bruit + air + présence) via ZoneTrack double radar. API ouverte (domotique Shelly, PMS). 4,99€/mois (Starter) vs ~12€ pour le leader. 100% EU, données horodatées comme preuve d'incident.

CONCURRENT : Minut (leader, 50 000+ clients) — détection mouvement seule, API fermée, cloud US, prix en hausse.

ANTI-POSITIONNEMENT (à ne jamais promettre) : pas de caméra, pas de micro, pas de détection mouvement seule, pas d'API fermée, pas de facturation par appareil.

SIGNATURE : « Noisyless ZoneTrack — chaque présence compte. »

PREUVES : early adopter Francis Dumortier (Villas-Des-Eaux) quitte Minut. 211 000 hébergements courte durée en France. Marché location courte durée : 148 Md$.

TON ÉDITORIAL : expert mais accessible, orienté B2B hôtellerie / conciergerie / gestion locative. Concret (chiffres, scénarios réels du terrain), jamais vendeur agressif ni corporate creux. Parle directement aux gestionnaires, conciergeries, hôteliers et propriétaires exigeants."""

NOISYLESS_KEYWORDS = "gestion locative Airbnb, nuisances sonores, fêtes non autorisées, sur-occupation, review 1 étoile, statut SuperHost, conciergerie Airbnb, protection du bien, détection de présence sans caméra, qualité d'air intérieur, RGPD hébergement France, alternative Minut, API domotique Shelly, hôtellerie connectée, tranquillité du propriétaire, preuve d'incident horodatée"


def run_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        _add_posts_account_id(conn)
        _backfill_accounts_from_personas(conn)
        _seed_positioning(conn)


def _seed_positioning(conn) -> None:
    # Table peut ne pas exister sur de très vieilles bases avant create_all — garde
    tables = [r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))]
    if "positionings" not in tables:
        return
    row = conn.execute(text("SELECT id, content FROM positionings WHERE bu = 'noisyless'")).first()
    if row is None:
        conn.execute(text(
            "INSERT INTO positionings (id, bu, content, keywords, created_at, updated_at) "
            "VALUES (:id, 'noisyless', :content, :kw, datetime('now'), datetime('now'))"
        ), {"id": str(uuid.uuid4()), "content": NOISYLESS_POSITIONING, "kw": NOISYLESS_KEYWORDS})
        logger.info("Migration: positionnement Noisyless seedé")
    elif not (row[1] or "").strip():
        conn.execute(text("UPDATE positionings SET content = :content, keywords = :kw WHERE bu = 'noisyless'"),
                     {"content": NOISYLESS_POSITIONING, "kw": NOISYLESS_KEYWORDS})
        logger.info("Migration: positionnement Noisyless rempli (était vide)")


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
