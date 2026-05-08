#!/usr/bin/env python3
"""Extract images from chat history — multi-IDE support.

Auto-detects: OpenCode, Claude Code, Cursor, or generic fallback.
Default: extract ALL images from the most recent message that contains images.
With --last N: extract the last N images chronologically.
Outputs JSON with image paths, metadata, and detected IDE.
"""
import base64
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

OUTPUT_DIR = Path.home() / ".cache/opencode/read-image"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXT = {"png": "png", "jpg": "jpg", "jpeg": "jpg", "webp": "webp", "gif": "gif"}


# ── Helpers ────────────────────────────────────────────────────────────────

def decode_base64(data: str) -> bytes | None:
    """Decode base64 data — handles both data: URLs and raw base64."""
    if "data:" in data and "base64," in data:
        data = data.split("base64,", 1)[1]
    elif data.startswith("data:"):
        data = data.split(",", 1)[1]
    try:
        return base64.b64decode(data)
    except Exception:
        return None


def get_extension(filename: str, mime: str) -> str:
    if "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in SUPPORTED_EXT:
            return SUPPORTED_EXT[ext]
    for keyword, ext in [("png", "png"), ("jpeg", "jpg"), ("jpg", "jpg"),
                         ("webp", "webp"), ("gif", "gif")]:
        if keyword in mime:
            return ext
    return "png"


def save_image(raw: bytes, filename: str, mime: str, idx: int) -> dict:
    ext = get_extension(filename, mime)
    base_name = Path(filename).stem
    out_name = f"{base_name}_{idx}.{ext}"
    out_path = OUTPUT_DIR / out_name
    out_path.write_bytes(raw)
    return {
        "index": idx,
        "path": str(out_path),
        "filename": filename,
        "mime": mime,
    }


def no_images_error(ide: str) -> None:
    print(json.dumps({
        "ide": ide,
        "error": "No images found in the current chat session.",
        "images": [],
    }))
    sys.exit(1)


# ── IDE Detection ──────────────────────────────────────────────────────────

def detect_ide() -> str:
    """Detect which IDE/agent the model is running in."""
    # OpenCode: has env var + SQLite DB
    if os.environ.get("OPENCODE") == "1":
        return "opencode"
    # Claude Code: has env vars or config directory
    if os.environ.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY") is not None:
        return "claude-code"
    if (Path.home() / ".claude" / "projects").is_dir():
        # Double-check by looking for recent session files
        projects = Path.home() / ".claude" / "projects"
        for proj_dir in projects.iterdir():
            if proj_dir.is_dir() and any(proj_dir.glob("*.jsonl")):
                return "claude-code"
    # Cursor
    if (Path.home() / ".cursor").is_dir():
        return "cursor"
    if (Path.home() / "Library" / "Application Support" / "Cursor").is_dir():
        return "cursor"
    # OpenCode (DB exists even without env var)
    opendb = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
    if opendb.exists():
        return "opencode"
    return "unknown"


# ── OpenCode extractor ─────────────────────────────────────────────────────

def extract_opencode_latest() -> list[dict]:
    db = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
    if not db.exists():
        return []
    conn = sqlite3.connect(str(db))
    row = conn.execute(
        "SELECT message_id FROM part "
        "WHERE json_extract(data, '$.type') = 'file' "
        "ORDER BY time_created DESC LIMIT 1"
    ).fetchone()
    if not row:
        conn.close()
        return []
    latest_msg_id = row[0]
    rows = conn.execute(
        "SELECT data FROM part "
        "WHERE message_id = ? AND json_extract(data, '$.type') = 'file' "
        "ORDER BY time_created ASC",
        (latest_msg_id,),
    ).fetchall()
    conn.close()

    results = []
    for idx, (data_json,) in enumerate(rows, start=1):
        part = json.loads(data_json)
        url = part.get("url", "")
        raw = decode_base64(url)
        if not raw:
            continue
        results.append(save_image(raw, part.get("filename", f"image{idx}.png"),
                                 part.get("mime", "image/png"), idx))
    return results


def extract_opencode_last(n: int) -> list[dict]:
    db = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
    if not db.exists():
        return []
    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT data FROM part "
        "WHERE json_extract(data, '$.type') = 'file' "
        "ORDER BY time_created DESC LIMIT ?",
        (n,),
    ).fetchall()
    conn.close()
    results = []
    for idx, (data_json,) in enumerate(reversed(rows), start=1):
        part = json.loads(data_json)
        url = part.get("url", "")
        raw = decode_base64(url)
        if not raw:
            continue
        results.append(save_image(raw, part.get("filename", f"image{idx}.png"),
                                 part.get("mime", "image/png"), idx))
    return results


# ── Claude Code extractor ──────────────────────────────────────────────────

def _find_latest_claude_session() -> Path | None:
    """Find the most recently modified session JSONL file."""
    projects = Path.home() / ".claude" / "projects"
    if not projects.is_dir():
        return None
    best_mtime = 0
    best_path = None
    for proj_dir in projects.iterdir():
        if not proj_dir.is_dir():
            continue
        for f in proj_dir.glob("*.jsonl"):
            mtime = f.stat().st_mtime
            if mtime > best_mtime:
                best_mtime = mtime
                best_path = f
    return best_path


def _extract_images_from_claude_content(content: list, idx_start: int) -> list[dict]:
    """Extract images from a Claude Code message content array."""
    results = []
    idx = idx_start
    for item in content:
        if isinstance(item, dict) and item.get("type") == "image":
            source = item.get("source", {})
            if source.get("type") == "base64":
                b64data = source.get("data", "")
                raw = decode_base64(b64data)
                if raw:
                    media = source.get("media_type", "image/png")
                    ext = "png"
                    if media:
                        for keyword, e in [("png", "png"), ("jpeg", "jpg"),
                                          ("jpg", "jpg"), ("webp", "webp"), ("gif", "gif")]:
                            if keyword in media:
                                ext = e
                                break
                    results.append(save_image(raw, f"image{idx}.{ext}", media, idx))
                    idx += 1
    return results


def extract_claude_code() -> list[dict]:
    """Extract images from the latest user message in the most recent session."""
    session_path = _find_latest_claude_session()
    if not session_path:
        return []

    with open(session_path, "r") as f:
        lines = f.readlines()

    # Scan backwards for the latest user message with image content
    for line in reversed(lines):
        try:
            obj = json.loads(line.strip())
        except json.JSONDecodeError:
            continue

        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue

        content = msg.get("content")
        if isinstance(content, list):
            images = _extract_images_from_claude_content(content, 1)
            if images:
                return images

        # Also check top-level content (simpler format)
        content2 = obj.get("content")
        if isinstance(content2, list):
            images = _extract_images_from_claude_content(content2, 1)
            if images:
                return images

    return []


# ── Cursor extractor ──────────────────────────────────────────────────────

_CURSOR_DB_PATHS = [
    Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb",
    Path.home() / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb",
]

_B64_IMAGE_RE = re.compile(r"data:image/(png|jpeg|jpg|webp|gif);base64,([A-Za-z0-9+/=]+)")


def _cursor_db() -> Path | None:
    for p in _CURSOR_DB_PATHS:
        if p.exists():
            return p
    return None


def _extract_base64_images_from_text(text: str, idx_start: int) -> list[dict]:
    """Extract base64 data: URLs from text content."""
    results = []
    idx = idx_start
    for m in _B64_IMAGE_RE.finditer(text):
        img_type = m.group(1)
        b64data = m.group(2)
        raw = decode_base64(b64data)
        if raw:
            ext = img_type if img_type != "jpeg" else "jpg"
            results.append(save_image(raw, f"image{idx}.{ext}",
                                     f"image/{img_type}", idx))
            idx += 1
    return results


def _extract_hex_images_from_text(text: str, idx_start: int) -> list[dict]:
    """Extract hex-encoded images (Uint8Array format) from text content."""
    results = []
    idx = idx_start
    # Pattern: {"type":"image","image":{"__type":"Uint8Array","hex":"..."}}
    hex_pattern = re.compile(
        r'\{"type"\s*:\s*"image"\s*,\s*"image"\s*:\s*\{'
        r'[^}]*"__type"\s*:\s*"Uint8Array"\s*,\s*'
        r'"hex"\s*:\s*"([0-9a-fA-F]+)"'
    )
    for m in hex_pattern.finditer(text):
        hex_data = m.group(1)
        try:
            raw = bytes.fromhex(hex_data)
        except ValueError:
            continue
        # Detect image type from magic bytes
        mime = "image/png"
        ext = "png"
        if raw[:4] == b"\x89PNG":
            mime = "image/png"
            ext = "png"
        elif raw[:2] == b"\xff\xd8":
            mime = "image/jpeg"
            ext = "jpg"
        elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            mime = "image/webp"
            ext = "webp"
        elif raw[:3] in (b"GIF", b"GIF"):
            mime = "image/gif"
            ext = "gif"
        results.append(save_image(raw, f"image{idx}.{ext}", mime, idx))
        idx += 1
    return results


def extract_cursor_latest() -> list[dict]:
    """Extract images from the latest Cursor agent conversation blob."""
    db_path = _cursor_db()
    if not db_path:
        return []

    conn = sqlite3.connect(str(db_path))

    # Find the most recent blob that contains image data
    row = conn.execute("""
        SELECT CAST(value AS TEXT)
        FROM cursorDiskKV
        WHERE key LIKE 'agentKv:blob:%'
        AND (
            CAST(value AS TEXT) LIKE '%data:image/%'
            OR CAST(value AS TEXT) LIKE '%"__type":"Uint8Array"%'
        )
        ORDER BY rowid DESC
        LIMIT 1
    """).fetchone()
    conn.close()

    if not row:
        return []

    text = row[0]
    results = []
    results.extend(_extract_base64_images_from_text(text, 1))
    start_idx = len(results) + 1
    results.extend(_extract_hex_images_from_text(text, start_idx))
    return results


def extract_cursor_last(n: int) -> list[dict]:
    """Extract the last N images across the most recent Cursor blobs."""
    db_path = _cursor_db()
    if not db_path:
        return []

    conn = sqlite3.connect(str(db_path))

    rows = conn.execute("""
        SELECT CAST(value AS TEXT)
        FROM cursorDiskKV
        WHERE key LIKE 'agentKv:blob:%'
        AND (
            CAST(value AS TEXT) LIKE '%data:image/%'
            OR CAST(value AS TEXT) LIKE '%"__type":"Uint8Array"%'
        )
        ORDER BY rowid DESC
        LIMIT 50
    """).fetchall()
    conn.close()

    results = []
    for (text,) in rows:
        results.extend(_extract_base64_images_from_text(text, len(results) + 1))
        results.extend(_extract_hex_images_from_text(text, len(results) + 1))
        if len(results) >= n:
            break

    return results[:n]


def extract_cursor() -> list[dict]:
    return extract_cursor_latest()


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    ide = detect_ide()

    if "--help" in sys.argv or "-h" in sys.argv:
        print(f"Detected IDE: {ide}")
        print()
        print("Usage: python extract_images.py [--last N]")
        print()
        print("  Default: extract ALL images from the most recent message with images.")
        print("  --last N: extract the last N images chronologically.")
        print()
        print("Supported IDEs:")
        print("  OpenCode    — extracts from SQLite database (full support)")
        print("  Claude Code — extracts from session JSONL files (full support)")
        print("  Cursor      — extracts from state.vscdb agent blobs (full support)")
        print("  Unknown     — no images can be extracted")
        sys.exit(0)

    if "--last" in sys.argv:
        try:
            idx = sys.argv.index("--last")
            n = int(sys.argv[idx + 1])
        except (ValueError, IndexError):
            print(json.dumps({"error": "Usage: --last N (where N is a positive integer)"}))
            sys.exit(1)
        if ide == "opencode":
            images = extract_opencode_last(n)
        elif ide == "claude-code":
            images = extract_claude_code()
            if images and len(images) > n:
                images = images[-n:]
        elif ide == "cursor":
            images = extract_cursor_last(n)
        else:
            images = []
    else:
        if ide == "opencode":
            images = extract_opencode_latest()
        elif ide == "claude-code":
            images = extract_claude_code()
        elif ide == "cursor":
            images = extract_cursor()
        else:
            images = []

    if not images:
        no_images_error(ide)

    output = {
        "ide": ide,
        "count": len(images),
        "images": images,
    }
    print(json.dumps(output, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
