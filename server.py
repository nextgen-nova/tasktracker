
import json
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__, static_folder=None)


# =====================================================
# DATABASE CONFIGURATION
# =====================================================

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not configured."
    )

# Supabase/Neon compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)


# =====================================================
# DATABASE INITIALIZATION
# =====================================================

def init_db():
    with engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS app_state (
                    id INTEGER PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        )


# =====================================================
# STATE MANAGEMENT
# =====================================================

def read_state():
    init_db()

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT payload
                FROM app_state
                WHERE id = 1
                """
            )
        ).fetchone()

    if not row:
        return None

    payload = row[0]

    if isinstance(payload, str):
        return json.loads(payload)

    return payload


def write_state(state):
    init_db()

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO app_state (
                    id,
                    payload,
                    updated_at
                )
                VALUES (
                    1,
                    CAST(:payload AS JSONB),
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (id)
                DO UPDATE SET
                    payload = CAST(:payload AS JSONB),
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            {
                "payload": json.dumps(state)
            }
        )


# =====================================================
# API ENDPOINTS
# =====================================================

@app.get("/api/tasktracker/state")
def get_tasktracker_state():
    return jsonify({
        "state": read_state()
    })


@app.post("/api/tasktracker/state")
@app.put("/api/tasktracker/state")
def save_tasktracker_state():
    data = request.get_json(silent=True) or {}

    state = data.get("state")

    if not isinstance(state, dict):
        return jsonify({
            "error": "state must be an object"
        }), 400

    write_state(state)

    return jsonify({
        "ok": True
    })


# =====================================================
# FRONTEND ROUTES
# =====================================================

@app.get("/")
def index():
    return send_from_directory(
        BASE_DIR,
        "index.html"
    )


@app.get("/<path:path>")
def static_files(path):
    if path.startswith("api/"):
        return jsonify({
            "error": "not found"
        }), 404

    return send_from_directory(
        BASE_DIR,
        path
    )


# =====================================================
# LOCAL DEVELOPMENT
# =====================================================

if __name__ == "__main__":
    init_db()

    port = int(
        os.environ.get(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )

