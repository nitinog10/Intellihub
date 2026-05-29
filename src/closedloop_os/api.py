from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from closedloop_os.config import get_settings
from closedloop_os.intelligence import IntelligenceService
from closedloop_os.mcp_server import mcp
from closedloop_os.messaging import EventPublisher, build_publisher
from closedloop_os.persistence import EventRepository, build_repository
from closedloop_os.search import build_knowledge_store
from closedloop_os.security import (
    verify_github_signature,
    verify_linear_signature,
    verify_sha256_signature,
    verify_slack_signature,
)
from closedloop_os.services import GitHubIngestService, RawIngestService
from closedloop_os.transcripts import chunk_transcript, parse_transcript
from closedloop_os.ui import LOCAL_CONSOLE_HTML

settings = get_settings()

CONNECTOR_CONFIG: dict[str, dict[str, object]] = {
    "github": {
        "label": "GitHub",
        "keys": ["GITHUB_WEBHOOK_SECRET"],
        "endpoint": "/api/connectors/github",
        "note": "Use this secret when creating the GitHub webhook.",
    },
    "slack": {
        "label": "Slack",
        "keys": ["SLACK_SIGNING_SECRET", "SLACK_BOT_TOKEN"],
        "endpoint": "/api/connectors/slack",
        "note": "Slack needs the signing secret and bot token.",
    },
    "linear": {
        "label": "Linear",
        "keys": ["LINEAR_WEBHOOK_SECRET"],
        "endpoint": "/api/connectors/linear",
        "note": "Use this secret for Linear webhook signature verification.",
    },
    "jira": {
        "label": "Jira",
        "keys": ["JIRA_ACCESS_TOKEN", "JIRA_WEBHOOK_SECRET"],
        "endpoint": "/api/connectors/jira",
        "note": "Jira OAuth is external for now; paste the access token here.",
    },
    "confluence": {
        "label": "Confluence",
        "keys": ["CONFLUENCE_ACCESS_TOKEN", "CONFLUENCE_WEBHOOK_SECRET"],
        "endpoint": "/api/connectors/confluence",
        "note": "Confluence OAuth is external for now; paste the access token here.",
    },
    "notion": {
        "label": "Notion",
        "keys": ["NOTION_ACCESS_TOKEN", "NOTION_DATABASE_ID", "NOTION_API_VERSION"],
        "endpoint": "timer sync",
        "note": "Notion is synced by the background scheduler, not a public webhook endpoint.",
    },
    "zendesk": {
        "label": "Zendesk",
        "keys": ["ZENDESK_WEBHOOK_SECRET"],
        "endpoint": "/api/connectors/zendesk",
        "note": "Use this secret for Zendesk webhook verification.",
    },
}

ALLOWED_CONNECTOR_KEYS = {
    key
    for connector in CONNECTOR_CONFIG.values()
    for key in connector["keys"]
}


class AskIntelligenceRequest(BaseModel):
    question: str = Field(min_length=1)


class SemanticSearchRequest(BaseModel):
    query_text: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
    source_tool: str | None = None


class EntityRequest(BaseModel):
    entity: str = Field(min_length=1)
    limit: int = Field(default=25, ge=1, le=100)


class QueryTextRequest(BaseModel):
    query_text: str | None = None
    limit: int = Field(default=25, ge=1, le=100)


class ConnectorSettingsRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


def _local_settings_path() -> Path:
    return Path("local.settings.json")


def _read_local_settings() -> dict:
    path = _local_settings_path()
    if not path.exists():
        return {"IsEncrypted": False, "Values": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="local.settings.json is not valid JSON.") from exc
    data.setdefault("IsEncrypted", False)
    data.setdefault("Values", {})
    return data


def _write_local_settings(data: dict) -> None:
    _local_settings_path().write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _refresh_runtime_settings(values: dict[str, str]) -> None:
    global settings
    for key, value in values.items():
        os.environ[key] = value
    get_settings.cache_clear()
    settings = get_settings()


def _masked(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:3]}...{value[-3:]}"


def _connector_status(values: dict[str, str]) -> dict[str, object]:
    connectors: dict[str, object] = {}
    for connector_id, config in CONNECTOR_CONFIG.items():
        keys = list(config["keys"])
        key_states = {
            key: {
                "configured": bool(values.get(key)),
                "preview": _masked(str(values.get(key, ""))),
            }
            for key in keys
        }
        required_keys = [key for key in keys if key != "NOTION_API_VERSION"]
        connectors[connector_id] = {
            "label": config["label"],
            "endpoint": config["endpoint"],
            "note": config["note"],
            "connected": all(bool(values.get(key)) for key in required_keys),
            "keys": key_states,
        }
    return {
        "connectors": connectors,
        "local_settings": str(_local_settings_path()),
    }


def get_repository() -> EventRepository:
    return build_repository()


def get_publisher() -> EventPublisher:
    return build_publisher()


def resolve_github_secret() -> str:
    return settings.github_webhook_secret


def resolve_slack_signing_secret() -> str:
    return settings.slack_signing_secret


def resolve_slack_bot_token() -> str:
    return settings.slack_bot_token


def resolve_linear_secret() -> str:
    return settings.linear_webhook_secret


def resolve_jira_access_token() -> str:
    return settings.jira_access_token


def resolve_jira_webhook_secret() -> str:
    return settings.jira_webhook_secret


def resolve_confluence_access_token() -> str:
    return settings.confluence_access_token


def resolve_confluence_webhook_secret() -> str:
    return settings.confluence_webhook_secret


def resolve_notion_access_token() -> str:
    return settings.notion_access_token


def resolve_zendesk_webhook_secret() -> str:
    return settings.zendesk_webhook_secret


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Start APScheduler for Notion sync background job
    from apscheduler.schedulers.background import BackgroundScheduler
    from closedloop_os.services import NotionSyncService

    scheduler = BackgroundScheduler()

    def _sync_notion_pages() -> None:
        try:
            service = NotionSyncService(repository=build_repository(), publisher=build_publisher())
            service.sync_updated_pages()
        except Exception:
            pass  # non-critical background job; log if needed

    interval_minutes = settings.notion_sync_interval_minutes
    if settings.notion_access_token:
        scheduler.add_job(
            _sync_notion_pages,
            "interval",
            minutes=interval_minutes,
            id="notion-sync",
            replace_existing=True,
        )
    scheduler.start()

    async with mcp.session_manager.run():
        yield

    scheduler.shutdown(wait=False)


app = FastAPI(title="ClosedLoop OS", version="0.1.0", lifespan=lifespan)
app.mount("/mcp", mcp.streamable_http_app())


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    return await local_ui()


@app.get("/api/status")
async def api_status() -> dict[str, object]:
    return {
        "name": "ClosedLoop OS",
        "status": "running",
        "cosmos_db": "connected" if settings.has_cosmos else "not configured",
        "openai": "connected" if settings.has_openai else "not configured (heuristic fallback)",
        "ui": "/ui",
        "health": "/healthz",
        "docs": "/docs",
        "connectors": [
            "/api/connectors/github",
            "/api/connectors/slack",
            "/api/connectors/linear",
            "/api/connectors/jira",
            "/api/connectors/confluence",
            "/api/connectors/zendesk",
            "/api/connectors/meetings/upload",
        ],
        "mcp": "/mcp",
        "mcp_info": "/mcp-info",
    }


@app.get("/ui", response_class=HTMLResponse)
async def local_ui() -> str:
    return LOCAL_CONSOLE_HTML


@app.get("/mcp-info")
async def mcp_info() -> dict[str, object]:
    return {
        "message": "/mcp is a Streamable HTTP MCP protocol endpoint. A normal browser GET is not a valid MCP call.",
        "mcp_url": "http://127.0.0.1:8000/mcp",
        "browser_ui": "/ui",
        "api_docs": "/docs",
        "tools": [
            "query_github_events",
            "get_event_by_id",
            "search_decisions",
            "get_slack_context",
            "get_linear_sprint_status",
            "semantic_search",
            "get_jira_epic_status",
            "get_notion_decisions",
            "analyze_meeting",
            "get_customer_signals",
            "get_entity_graph",
            "get_action_items",
            "ask_intelligence",
            "get_timeline",
        ],
    }


@app.get("/api/connectors/config")
async def get_connector_config() -> dict[str, object]:
    data = _read_local_settings()
    return _connector_status(data["Values"])


@app.post("/api/connectors/config")
async def save_connector_config(payload: ConnectorSettingsRequest) -> dict[str, object]:
    unknown = sorted(set(payload.values) - ALLOWED_CONNECTOR_KEYS)
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unsupported connector setting(s): {', '.join(unknown)}")

    cleaned = {
        key: value.strip()
        for key, value in payload.values.items()
        if value is not None and value.strip()
    }
    if not cleaned:
        raise HTTPException(status_code=400, detail="No connector settings were provided.")

    data = _read_local_settings()
    data["Values"].update(cleaned)
    _write_local_settings(data)
    _refresh_runtime_settings(cleaned)

    return {
        "saved": sorted(cleaned),
        **_connector_status(data["Values"]),
    }


@app.post("/api/demo/zendesk")
async def demo_zendesk_event(publisher: EventPublisher = Depends(get_publisher)) -> dict[str, object]:
    payload = {
        "type": "sla.breached",
        "id": "local-zendesk-sla",
        "ticket": {
            "id": 99,
            "subject": "Enterprise outage",
            "description": "SLA is breached for ENG-101 customer impact.",
            "updated_at": "2026-05-28T16:30:00Z",
        },
    }
    raw_event = RawIngestService(publisher=publisher).ingest(
        source_tool="zendesk",
        event_name="sla.breached",
        payload=payload,
        delivery_id="local-zendesk-sla",
    )
    return {
        "status": "accepted",
        "raw_event_id": raw_event.id,
        "event_type": raw_event.event_name,
        "note": "Event is processed immediately by the in-process pipeline.",
    }


@app.post("/api/tools/ask-intelligence")
async def ask_intelligence_tool(payload: AskIntelligenceRequest) -> dict:
    service = IntelligenceService(repository=build_repository(), knowledge_store=build_knowledge_store())
    return service.ask_intelligence(payload.question).model_dump(mode="json")


@app.post("/api/tools/semantic-search")
async def semantic_search_tool(payload: SemanticSearchRequest) -> list[dict]:
    return build_knowledge_store().semantic_search(
        query_text=payload.query_text,
        limit=payload.limit,
        source_tool=payload.source_tool,
    )


@app.post("/api/tools/entity-graph")
async def entity_graph_tool(payload: EntityRequest) -> list[dict]:
    return build_repository().get_entity_graph(entity=payload.entity, limit=payload.limit)


@app.post("/api/tools/timeline")
async def timeline_tool(payload: EntityRequest) -> list[dict]:
    service = IntelligenceService(repository=build_repository(), knowledge_store=build_knowledge_store())
    return service.get_timeline(entity=payload.entity, limit=payload.limit)


@app.post("/api/tools/customer-signals")
async def customer_signals_tool(payload: QueryTextRequest) -> list[dict]:
    return build_repository().get_customer_signals(limit=payload.limit)


@app.post("/api/tools/action-items")
async def action_items_tool(payload: QueryTextRequest) -> list[dict]:
    return build_repository().get_action_items(query_text=payload.query_text, limit=payload.limit)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/connectors/github", status_code=status.HTTP_202_ACCEPTED)
async def github_connector(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    repository: EventRepository = Depends(get_repository),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    body = await request.body()
    secret = resolve_github_secret()
    if not verify_github_signature(secret, body, x_hub_signature_256):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GitHub webhook signature.")

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    service = GitHubIngestService(repository=repository, publisher=publisher)
    try:
        event = service.ingest(event_name=x_github_event, payload=payload, delivery_id=x_github_delivery)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"status": "accepted", "event_id": event.id, "event_type": event.event_type}


@app.post("/api/connectors/slack", status_code=status.HTTP_202_ACCEPTED)
async def slack_connector(
    request: Request,
    response: Response,
    x_slack_signature: str | None = Header(default=None, alias="X-Slack-Signature"),
    x_slack_request_timestamp: str | None = Header(default=None, alias="X-Slack-Request-Timestamp"),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    body = await request.body()
    if not verify_slack_signature(resolve_slack_signing_secret(), body, x_slack_signature, x_slack_request_timestamp):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Slack signature.")

    # OAuth2 bot token is resolved here so deployment fails early if the connector is configured incompletely.
    resolve_slack_bot_token()

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    if payload.get("type") == "url_verification":
        response.status_code = status.HTTP_200_OK
        return {"challenge": payload.get("challenge", "")}

    event = payload.get("event", {})
    event_type = event.get("type")
    if event_type not in {"message", "file_shared"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported Slack event '{event_type}'.")

    delivery_id = payload.get("event_id") or f"slack-{event.get('event_ts') or event.get('ts')}"
    raw_event = RawIngestService(publisher=publisher).ingest(
        source_tool="slack",
        event_name=event_type,
        payload=payload,
        delivery_id=delivery_id,
    )
    return {"status": "accepted", "raw_event_id": raw_event.id, "event_type": event_type}


@app.post("/api/connectors/linear", status_code=status.HTTP_202_ACCEPTED)
async def linear_connector(
    request: Request,
    linear_signature: str | None = Header(default=None, alias="Linear-Signature"),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    body = await request.body()
    if not verify_linear_signature(resolve_linear_secret(), body, linear_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Linear signature.")

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    linear_type = (payload.get("type") or payload.get("data", {}).get("__typename") or "").lower()
    if linear_type not in {"issue", "comment", "cycle", "project"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported Linear event '{linear_type}'.")

    delivery_id = payload.get("webhookId") or payload.get("id") or f"linear-{linear_type}-{payload.get('action', 'event')}"
    raw_event = RawIngestService(publisher=publisher).ingest(
        source_tool="linear",
        event_name=linear_type,
        payload=payload,
        delivery_id=delivery_id,
    )
    return {"status": "accepted", "raw_event_id": raw_event.id, "event_type": linear_type}


@app.post("/api/connectors/jira", status_code=status.HTTP_202_ACCEPTED)
async def jira_connector(
    request: Request,
    x_atlassian_webhook_identifier: str | None = Header(default=None, alias="X-Atlassian-Webhook-Identifier"),
    x_atlassian_webhook_event: str | None = Header(default=None, alias="X-Atlassian-Webhook-Event"),
    x_closedloop_signature: str | None = Header(default=None, alias="X-ClosedLoop-Signature"),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    body = await request.body()
    secret = resolve_jira_webhook_secret()
    if secret and not verify_sha256_signature(secret, body, x_closedloop_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Jira signature.")
    resolve_jira_access_token()

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    event_name = (x_atlassian_webhook_event or payload.get("webhookEvent") or "").lower().replace("jira:", "").replace("comment_", "comment_")
    supported = {"issue_created", "issue_updated", "comment_created", "sprint_started", "sprint_closed"}
    if event_name not in supported:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported Jira event '{event_name}'.")

    delivery_id = str(x_atlassian_webhook_identifier or payload.get("timestamp") or f"jira-{event_name}")
    raw_event = RawIngestService(publisher=publisher).ingest("jira", event_name, payload, delivery_id)
    return {"status": "accepted", "raw_event_id": raw_event.id, "event_type": event_name}


@app.post("/api/connectors/confluence", status_code=status.HTTP_202_ACCEPTED)
async def confluence_connector(
    request: Request,
    x_atlassian_webhook_identifier: str | None = Header(default=None, alias="X-Atlassian-Webhook-Identifier"),
    x_closedloop_signature: str | None = Header(default=None, alias="X-ClosedLoop-Signature"),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    body = await request.body()
    secret = resolve_confluence_webhook_secret()
    if secret and not verify_sha256_signature(secret, body, x_closedloop_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Confluence signature.")
    resolve_confluence_access_token()

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    delivery_id = str(x_atlassian_webhook_identifier or payload.get("timestamp") or "confluence-event")
    raw_event = RawIngestService(publisher=publisher).ingest(
        source_tool="confluence",
        event_name=payload.get("eventType", "page_updated"),
        payload=payload,
        delivery_id=delivery_id,
    )
    return {"status": "accepted", "raw_event_id": raw_event.id, "event_type": raw_event.event_name}


@app.post("/api/connectors/zendesk", status_code=status.HTTP_202_ACCEPTED)
async def zendesk_connector(
    request: Request,
    x_zendesk_webhook_signature: str | None = Header(default=None, alias="X-Zendesk-Webhook-Signature"),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    body = await request.body()
    secret = resolve_zendesk_webhook_secret()
    if secret and not verify_sha256_signature(secret, body, x_zendesk_webhook_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Zendesk signature.")

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc

    event_name = (payload.get("type") or payload.get("event_type") or "").lower()
    supported = {"ticket.created", "ticket.updated", "sla.breached", "satisfaction_rated"}
    if event_name not in supported:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported Zendesk event '{event_name}'.")

    delivery_id = str(payload.get("id") or payload.get("ticket", {}).get("id") or f"zendesk-{event_name}")
    raw_event = RawIngestService(publisher=publisher).ingest("zendesk", event_name, payload, delivery_id)
    return {"status": "accepted", "raw_event_id": raw_event.id, "event_type": event_name}


@app.post("/api/connectors/meetings/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_meeting_transcript(
    file: UploadFile = File(...),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict[str, object]:
    supported = {".txt", ".vtt", ".srt", ".json"}
    filename = file.filename or "meeting.txt"
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in supported:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported transcript file '{suffix}'.")

    content = await file.read()
    parsed_chunks = parse_transcript(filename, content)
    grouped = chunk_transcript(parsed_chunks)
    delivery_id = f"meeting-{uuid4()}"
    meeting_id = f"meeting-{uuid4()}"
    payload = {
        "meeting_id": meeting_id,
        "title": filename,
        "filename": filename,
        "grouped_chunks": [
            {"speaker": chunk.speaker, "timestamp": chunk.timestamp, "text": chunk.text}
            for chunk in grouped
        ],
    }
    raw_event = RawIngestService(publisher=publisher).ingest("meeting", "transcript_upload", payload, delivery_id)
    return {
        "status": "accepted",
        "raw_event_id": raw_event.id,
        "meeting_id": meeting_id,
        "chunk_count": len(grouped),
    }
