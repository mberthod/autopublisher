from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app.models import Post

router = APIRouter()


@router.get("")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Post).count()
    by_status = dict(
        db.query(Post.status, func.count(Post.id))
        .group_by(Post.status)
        .all()
    )
    by_platform = dict(
        db.query(Post.platform, func.count(Post.id))
        .group_by(Post.platform)
        .all()
    )
    published = by_status.get("published", 0)
    scheduled = by_status.get("scheduled", 0)
    draft = by_status.get("draft", 0)
    failed = by_status.get("failed", 0)
    return {
        "total_posts": total,
        "published": published,
        "scheduled": scheduled,
        "draft": draft,
        "failed": failed,
        "by_platform": by_platform,
        "success_rate": round(published / max(published + failed, 1) * 100, 1),
    }
