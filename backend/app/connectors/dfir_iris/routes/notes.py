from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger

from app.connectors.dfir_iris.schema.notes import NoteCreationBody
from app.connectors.dfir_iris.schema.notes import NoteCreationResponse
from app.connectors.dfir_iris.schema.notes import NotesResponse
from app.connectors.dfir_iris.services.notes import create_case_note
from app.connectors.dfir_iris.services.notes import get_case_notes
from app.connectors.dfir_iris.utils.universal import check_case_exists


def verify_case_exists(case_id: int) -> int:
    if not check_case_exists(case_id):
        raise HTTPException(status_code=400, detail=f"Case {case_id} does not exist.")
    return case_id


notes_router = APIRouter()


@notes_router.get("/{case_id}", response_model=NotesResponse, description="Get all notes for a case")
async def get_case_notes_route(case_id: int = Depends(verify_case_exists), search_term: Optional[str] = "%") -> NotesResponse:
    logger.info(f"Fetching notes for case {case_id}")
    return get_case_notes(case_id, search_term)


@notes_router.post("/{case_id}", response_model=NoteCreationResponse, description="Create a note for a case")
async def create_case_note_route(case_id: int, note_creation_body: NoteCreationBody) -> NoteCreationResponse:
    verify_case_exists(case_id)
    logger.info(f"Creating a note for case {case_id}")
    return create_case_note(case_id, note_creation_body)