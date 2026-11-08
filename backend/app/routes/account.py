from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, Response

from app.account import AuthAdmin, delete_account, get_auth_admin
from app.auth import CurrentUser, get_current_user
from app.db import get_db
from app.errors import error_responses

router = APIRouter(prefix="/api/account", tags=["account"])


@router.delete(
    "",
    status_code=204,
    summary="Delete my account",
    description="Permanently deletes the user's symptom descriptions, attempts, recommendation "
    "results and ratings, then the account itself.",
    responses=error_responses(401, 502),
)
def delete_my_account(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[psycopg.Connection, Depends(get_db)],
    admin: Annotated[AuthAdmin, Depends(get_auth_admin)],
) -> Response:
    delete_account(db, admin, user.id)
    return Response(status_code=204)
