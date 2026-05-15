import sqlite3
from contextlib import closing

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DB_PATH = "chatroom.db"
MAX_CONTENT_BYTES = 8192
DEFAULT_ROOM = "main"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


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


class PostMessageIn(BaseModel):
    author: str
    content: str
    room: str = DEFAULT_ROOM


app = FastAPI()


def row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "room": row["room"],
        "author": row["author"],
        "content": row["content"],
        "created_at": row["created_at"],
    }


@app.post("/api/messages")
def post_message(msg: PostMessageIn) -> dict:
    if len(msg.content.encode("utf-8")) > MAX_CONTENT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"content exceeds {MAX_CONTENT_BYTES} bytes",
        )
    if not msg.author.strip() or not msg.content.strip():
        raise HTTPException(status_code=400, detail="author and content required")

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "INSERT INTO messages (room, author, content) VALUES (?, ?, ?)",
            (msg.room, msg.author, msg.content),
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


@app.get("/api/rooms/{room}/messages")
def list_messages(room: str, since_id: int = 0) -> list[dict]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT id, room, author, content, "
            f"strftime('{ISO_FORMAT}', created_at) AS created_at "
            f"FROM messages "
            f"WHERE room = ? AND id > ? "
            f"ORDER BY id DESC LIMIT 50",
            (room, since_id),
        ).fetchall()
    return [row_to_dict(r) for r in reversed(rows)]


app.mount("/", StaticFiles(directory="web", html=True), name="web")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
