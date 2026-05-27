from closedloop_os.mappers.github import map_github_event


def test_maps_pull_request_event():
    payload = {
        "action": "opened",
        "repository": {"full_name": "closedloop/example"},
        "sender": {"login": "octocat"},
        "pull_request": {
            "number": 42,
            "title": "Add ingestion flow",
            "body": "Normalizes events.",
            "state": "open",
            "merged": False,
            "html_url": "https://github.com/closedloop/example/pull/42",
            "created_at": "2026-05-27T08:00:00Z",
            "updated_at": "2026-05-27T08:30:00Z"
        }
    }

    event = map_github_event("pull_request", payload, "delivery-123")

    assert event.source_tool == "github"
    assert event.event_type == "github.pull_request.opened"
    assert event.project == "closedloop/example"
    assert event.actor == "octocat"
    assert event.metadata["pull_request_number"] == 42
