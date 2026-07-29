import hashlib
import hmac
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from dueflow.application.meta_webhooks import MetaWebhookService
from dueflow.infrastructure.db.dependencies import get_session
from dueflow.infrastructure.db.notification_repository import (
    NotificationAttemptRepository,
)

router = APIRouter(prefix="/webhooks/meta", tags=["webhooks"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("", response_class=PlainTextResponse)
def verify_meta_webhook(
    request: Request,
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    verify_token: Annotated[
        str | None,
        Query(alias="hub.verify_token"),
    ] = None,
    challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> str:
    configured = request.app.state.settings.meta_webhook_verify_token
    if configured is None:
        raise HTTPException(status_code=503, detail="webhook da Meta não configurado")
    expected = configured.get_secret_value()
    if (
        mode != "subscribe"
        or verify_token is None
        or challenge is None
        or not hmac.compare_digest(verify_token, expected)
    ):
        raise HTTPException(status_code=403, detail="verificação do webhook inválida")
    return challenge


@router.post("")
async def receive_meta_webhook(
    request: Request,
    session: SessionDependency,
    signature: Annotated[
        str | None,
        Header(alias="X-Hub-Signature-256"),
    ] = None,
) -> dict[str, int | bool]:
    configured = request.app.state.settings.meta_app_secret
    if configured is None:
        raise HTTPException(status_code=503, detail="webhook da Meta não configurado")
    raw_body = await request.body()
    expected = "sha256=" + hmac.new(
        configured.get_secret_value().encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    if signature is None or not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="assinatura do webhook inválida")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="payload do webhook inválido",
        ) from exc
    result = MetaWebhookService(
        NotificationAttemptRepository(session)
    ).process(payload)
    return {
        "received": True,
        "events": result.received,
        "updated": result.updated,
        "ignored": result.ignored,
        "unknown": result.unknown,
    }
