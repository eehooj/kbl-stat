"""Official visible registered-player directory, distinct from season statistics."""
import json

from sqlalchemy import select

from app.models import RawSourceDocument

ROSTER_URL = "https://www.kbl.or.kr/player/player"
MARKER = "REGISTERED_ROSTER_COMPLETE\n"


def latest_registered_roster(session):
    documents = session.scalars(select(RawSourceDocument).where(
        RawSourceDocument.source_url == ROSTER_URL,
    ).order_by(RawSourceDocument.fetched_at.desc()))
    for document in documents:
        body = json.loads(document.body).get("visible_text", "")
        if body.startswith(MARKER):
            return {tuple(line.split("\t")) for line in body[len(MARKER):].splitlines()}
    return set()
