"""Tests for the buggy TODO app. One test fails due to the delete bug."""

from fastapi.testclient import TestClient
from main import app, todos

client = TestClient(app)


def setup_function():
    todos.clear()


def test_create_todo():
    resp = client.post("/todos?title=Buy+milk")
    assert resp.status_code == 201
    assert resp.json()["title"] == "Buy milk"


def test_list_todos():
    client.post("/todos?title=Task+A")
    client.post("/todos?title=Task+B")
    resp = client.get("/todos")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_todo_not_found():
    resp = client.get("/todos/999")
    assert resp.status_code == 404


def test_delete_actually_removes_todo():
    """This test FAILS because delete doesn't actually remove the todo."""
    resp = client.post("/todos?title=Delete+me")
    todo_id = resp.json()["id"]

    del_resp = client.delete(f"/todos/{todo_id}")
    assert del_resp.status_code == 200

    # After deletion, the todo should be gone
    get_resp = client.get(f"/todos/{todo_id}")
    assert get_resp.status_code == 404, "Bug: todo still exists after DELETE"
