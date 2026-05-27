from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from closedloop_os.models import CanonicalEvent


def _repo_name(payload: dict[str, Any]) -> str:
    return payload.get("repository", {}).get("full_name", "unknown/unknown")


def _actor(payload: dict[str, Any]) -> str:
    return (
        payload.get("sender", {}).get("login")
        or payload.get("pusher", {}).get("name")
        or payload.get("release", {}).get("author", {}).get("login")
        or "unknown"
    )


def _timestamp(*values: str | None) -> datetime:
    for value in values:
        if value:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def _importance(event_name: str, payload: dict[str, Any]) -> float:
    table = {
        "push": 0.55,
        "pull_request": 0.82,
        "issues": 0.7,
        "pull_request_review": 0.66,
        "release": 0.92,
        "workflow_run": 0.75,
    }
    score = table.get(event_name, 0.5)
    if event_name == "workflow_run" and payload.get("workflow_run", {}).get("conclusion") == "failure":
        score = 0.9
    if event_name == "pull_request" and payload.get("action") in {"closed", "merged"}:
        score = 0.88
    return score


def map_github_event(event_name: str, payload: dict[str, Any], delivery_id: str) -> CanonicalEvent:
    repo = _repo_name(payload)
    actor = _actor(payload)
    action = payload.get("action", "occurred")

    if event_name == "push":
        ref = payload.get("ref", "")
        branch = ref.split("/")[-1] if ref else "unknown"
        title = f"Push to {branch}"
        description = f"{actor} pushed {payload.get('commits', []) and len(payload['commits']) or 0} commit(s) to {repo}."
        timestamp = _timestamp(payload.get("head_commit", {}).get("timestamp"))
        metadata = {
            "delivery_id": delivery_id,
            "repository": repo,
            "branch": branch,
            "commit_count": len(payload.get("commits", [])),
            "compare_url": payload.get("compare"),
        }
        event_type = "github.push"
    elif event_name == "pull_request":
        pr = payload.get("pull_request", {})
        title = f"PR {action}: {pr.get('title', 'Untitled pull request')}"
        description = pr.get("body") or f"Pull request #{pr.get('number')} was {action}."
        timestamp = _timestamp(pr.get("updated_at"), pr.get("created_at"))
        metadata = {
            "delivery_id": delivery_id,
            "repository": repo,
            "pull_request_number": pr.get("number"),
            "state": pr.get("state"),
            "merged": pr.get("merged", False),
            "url": pr.get("html_url"),
        }
        event_type = f"github.pull_request.{action}"
    elif event_name == "issues":
        issue = payload.get("issue", {})
        title = f"Issue {action}: {issue.get('title', 'Untitled issue')}"
        description = issue.get("body") or f"Issue #{issue.get('number')} was {action}."
        timestamp = _timestamp(issue.get("updated_at"), issue.get("created_at"))
        metadata = {
            "delivery_id": delivery_id,
            "repository": repo,
            "issue_number": issue.get("number"),
            "state": issue.get("state"),
            "url": issue.get("html_url"),
        }
        event_type = f"github.issues.{action}"
    elif event_name == "pull_request_review":
        review = payload.get("review", {})
        pr = payload.get("pull_request", {})
        review_state = (review.get("state") or "submitted").lower()
        title = f"PR review {review_state}: {pr.get('title', 'Untitled pull request')}"
        description = review.get("body") or f"Review on PR #{pr.get('number')} is {review_state}."
        timestamp = _timestamp(review.get("submitted_at"), pr.get("updated_at"))
        metadata = {
            "delivery_id": delivery_id,
            "repository": repo,
            "pull_request_number": pr.get("number"),
            "review_state": review_state,
            "url": review.get("html_url") or pr.get("html_url"),
        }
        event_type = f"github.pull_request_review.{review_state}"
    elif event_name == "release":
        release = payload.get("release", {})
        title = f"Release {action}: {release.get('tag_name', 'untagged')}"
        description = release.get("body") or f"Release {release.get('name') or release.get('tag_name')} was {action}."
        timestamp = _timestamp(release.get("published_at"), release.get("created_at"))
        metadata = {
            "delivery_id": delivery_id,
            "repository": repo,
            "tag_name": release.get("tag_name"),
            "prerelease": release.get("prerelease", False),
            "url": release.get("html_url"),
        }
        event_type = f"github.release.{action}"
    elif event_name == "workflow_run":
        run = payload.get("workflow_run", {})
        conclusion = run.get("conclusion") or run.get("status") or action
        title = f"Workflow run {conclusion}: {run.get('name', 'Unnamed workflow')}"
        description = f"Workflow '{run.get('name', 'Unnamed workflow')}' on {repo} is {conclusion}."
        timestamp = _timestamp(run.get("updated_at"), run.get("created_at"))
        metadata = {
            "delivery_id": delivery_id,
            "repository": repo,
            "workflow_name": run.get("name"),
            "head_branch": run.get("head_branch"),
            "conclusion": run.get("conclusion"),
            "url": run.get("html_url"),
        }
        event_type = f"github.workflow_run.{conclusion}"
    else:
        raise ValueError(f"Unsupported GitHub event: {event_name}")

    return CanonicalEvent(
        source_tool="github",
        event_type=event_type,
        title=title,
        description=description,
        actor=actor,
        project=repo,
        importance_score=_importance(event_name, payload),
        timestamp=timestamp,
        raw_payload=payload,
        metadata=metadata,
    )
