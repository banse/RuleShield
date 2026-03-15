"""Simple FastAPI TODO app with an intentional bug for demo purposes."""

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Buggy TODO App")

todos: dict[int, dict] = {}
_next_id = 1


@app.get("/todos")
def list_todos():
    return list(todos.values())


@app.post("/todos", status_code=201)
def create_todo(title: str, done: bool = False):
    global _next_id
    todo = {"id": _next_id, "title": title, "done": done}
    todos[_next_id] = todo
    _next_id += 1
    return todo


@app.get("/todos/{todo_id}")
def get_todo(todo_id: int):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todos[todo_id]


@app.put("/todos/{todo_id}")
def update_todo(todo_id: int, title: str | None = None, done: bool | None = None):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    if title is not None:
        todos[todo_id]["title"] = title
    if done is not None:
        todos[todo_id]["done"] = done
    return todos[todo_id]


# BUG: This endpoint returns 200 and the todo, but never actually deletes it.
@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    todo = todos[todo_id]
    # Missing: del todos[todo_id]
    return {"detail": "Todo deleted", "id": todo_id}
