"""Saving documents. Every change is stored as a revision, so nothing the user wrote is overwritten for good."""
from sqlalchemy.orm import Session

from . import packs
from .models import Case, Document, DocumentRevision, JournalEntry, now

KINDS = {"change_request": "Change Request", "client_message": "Message to the client"}
MAX_LEN = 20000


def doc_label(situation_id: str, kind: str) -> str:
    if kind == "change_request":
        return (packs.get_situation(situation_id) or {}).get("documentName", KINDS[kind])
    return KINDS[kind]


def get_doc(c: Case, kind: str) -> Document | None:
    return next((d for d in c.documents if d.kind == kind), None)


def save_document(db: Session, c: Case, kind: str, body: str, source: str = "user", journal: bool = True) -> Document:
    """Create or update the document. Returns it; an unchanged body adds no revision."""
    doc = get_doc(c, kind)
    if doc is None:
        doc = Document(user_id=c.user_id, case_id=c.id, kind=kind, body=body)
        doc.revisions.append(DocumentRevision(body=body, source=source))
        c.documents.append(doc)
        if journal and source != "generated":
            db.add(JournalEntry(user_id=c.user_id, case_id=c.id, type="document", text=f"Saved: {doc_label(c.situation_id, kind)}. {packs.case_title(c.situation_id, c.inputs)}"))
    elif doc.body != body:
        doc.body = body
        doc.updated_at = now()
        doc.revisions.append(DocumentRevision(body=body, source=source))
        if journal:
            db.add(JournalEntry(user_id=c.user_id, case_id=c.id, type="document", text=f"Edited: {doc_label(c.situation_id, kind)}. {packs.case_title(c.situation_id, c.inputs)}"))
    return doc
