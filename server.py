import sqlite3
from contextlib import asynccontextmanager, closing

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

DB_PATH = "chatroom.db"
MAX_CONTENT_BYTES = 8192
DEFAULT_ROOM = "main"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
MCP_AUTHOR_STUB = "mcp-test"


def init_db() -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
              id          INTEGER PRIMARY KEY AUTOINCREMENT,
              room        TEXT NOT NULL DEFAULT 'main',
              author      TEXT NOT NULL,
              content     TEXT NOT NULL,
              created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_messages_room_created
              ON messages(room, created_at);
            """
        )
        conn.commit()


init_db()


def row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "room": row["room"],
        "author": row["author"],
        "content": row["content"],
        "created_at": row["created_at"],
    }


class ContentTooLargeError(ValueError):
    pass


def db_insert_message(room: str, author: str, content: str) -> dict:
    if not author.strip() or not content.strip():
        raise ValueError("author and content required")
    if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
        raise ContentTooLargeError(
            f"content exceeds {MAX_CONTENT_BYTES} bytes"
        )

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "INSERT INTO messages (room, author, content) VALUES (?, ?, ?)",
            (room, author, content),
        )
        new_id = cur.lastrowid
        conn.commit()
        row = conn.execute(
            f"SELECT id, room, author, content, "
            f"strftime('{ISO_FORMAT}', created_at) AS created_at "
            f"FROM messages WHERE id = ?",
            (new_id,),
        ).fetchone()
    return row_to_dict(row)


def db_list_messages(room: str, since_id: int = 0, limit: int = 50) -> list[dict]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT id, room, author, content, "
            f"strftime('{ISO_FORMAT}', created_at) AS created_at "
            f"FROM messages "
            f"WHERE room = ? AND id > ? "
            f"ORDER BY id DESC LIMIT ?",
            (room, since_id, limit),
        ).fetchall()
    return [row_to_dict(r) for r in reversed(rows)]


mcp = FastMCP("agent-parley", streamable_http_path="/")


@mcp.tool()
def post_message(content: str, room: str = DEFAULT_ROOM) -> dict:
    """Post a message to the chatroom. Returns the inserted row."""
    return db_insert_message(room=room, author=MCP_AUTHOR_STUB, content=content)


@mcp.tool()
def read_messages(
    room: str = DEFAULT_ROOM, since_id: int = 0, limit: int = 50
) -> list[dict]:
    """Read up to `limit` messages from the room, oldest-first."""
    return db_list_messages(room=room, since_id=since_id, limit=limit)


mcp_asgi_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(lifespan=lifespan)


class PostMessageIn(BaseModel):
    author: str
    content: str
    room: str = DEFAULT_ROOM


@app.post("/api/messages")
def post_message_rest(msg: PostMessageIn) -> dict:
    try:
        return db_insert_message(room=msg.room, author=msg.author, content=msg.content)
    except ContentTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/rooms/{room}/messages")
def list_messages_rest(room: str, since_id: int = 0) -> list[dict]:
    return db_list_messages(room=room, since_id=since_id)


@app.api_route("/mcp", methods=["GET", "POST", "DELETE", "OPTIONS"])
async def _mcp_trailing_slash() -> RedirectResponse:
    return RedirectResponse(url="/mcp/", status_code=307)


app.mount("/mcp", mcp_asgi_app)
app.mount("/", StaticFiles(directory="web", html=True), name="web")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
