#!/usr/bin/env python3
"""Analyze an image using a vision provider.

Supports:
  openrouter  — OpenRouter API (needs OPENROUTER_API_KEY)
  ollama      — Local Ollama (needs ollama CLI/server)

Output: plain text description of the image.
"""
import base64
import json
import os
import subprocess
import sys
from pathlib import Path


# ── Base64 helper ──────────────────────────────────────────────────────────

def image_to_base64(path: str) -> str:
    """Read an image file and return a base64 data URL."""
    p = Path(path)
    raw = p.read_bytes()
    b64 = base64.b64encode(raw).decode("utf-8")
    ext = p.suffix.lower().lstrip(".")
    mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp", "gif": "image/gif"}
    mime = mime_map.get(ext, "image/png")
    return f"data:{mime};base64,{b64}"


# ── OpenRouter ─────────────────────────────────────────────────────────────

OR_DEFAULT_MODEL = "google/gemini-2.5-flash"
OR_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def analyze_openrouter(image_path: str, prompt: str, api_key: str,
                       model: str = OR_DEFAULT_MODEL) -> str:
    """Call OpenRouter vision API."""
    data_url = image_to_base64(image_path)

    body = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }],
        "max_tokens": 1000,
    }

    import urllib.request
    import urllib.error

    req = urllib.request.Request(
        OR_API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/user/myskils",
            "X-Title": "read-image skill",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        return content.strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return f"OpenRouter error {e.code}: {body[:500]}"
    except Exception as e:
        return f"OpenRouter request failed: {e}"


# ── Ollama ─────────────────────────────────────────────────────────────────

OLLAMA_DEFAULT_MODEL = "llava:13b"
OLLAMA_API_URL = "http://localhost:11434/api/chat"


def analyze_ollama(image_path: str, prompt: str, model: str = OLLAMA_DEFAULT_MODEL) -> str:
    """Call local Ollama vision model."""
    p = Path(image_path)
    raw = p.read_bytes()
    b64 = base64.b64encode(raw).decode("utf-8")

    body = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": prompt,
            "images": [b64],
        }],
        "stream": False,
    }

    import urllib.request
    import urllib.error

    req = urllib.request.Request(
        OLLAMA_API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        content = result.get("message", {}).get("content", "")
        return content.strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return f"Ollama error {e.code}: {body[:500]}"
    except Exception as e:
        return f"Ollama request failed: {e}"


# ── Provider detection helpers ─────────────────────────────────────────────

def check_openrouter_available() -> dict | None:
    """Check if OpenRouter is configured. Returns config dict or None."""
    env_key = os.environ.get("OPENROUTER_API_KEY", "")
    env_model = os.environ.get("OPENROUTER_VISION_MODEL", "")
    if env_key:
        return {"api_key": env_key, "model": env_model or OR_DEFAULT_MODEL}
    # Check common config files
    for cfg_path in [
        Path.home() / ".openrouter" / "api_key",
        Path.home() / ".config" / "openrouter" / "api_key",
    ]:
        if cfg_path.is_file():
            return {"api_key": cfg_path.read_text().strip(),
                    "model": env_model or OR_DEFAULT_MODEL}
    return None


def check_ollama_available() -> dict | None:
    """Check if Ollama is installed and has a vision model. Returns config or None."""
    # Check if ollama CLI exists
    ollama_bin = None
    for p in os.environ.get("PATH", "").split(":"):
        candidate = Path(p) / "ollama"
        if candidate.is_file():
            ollama_bin = str(candidate)
            break
    if not ollama_bin:
        return None

    # Check if server is running and has a model
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = [m["name"] for m in data.get("models", [])]
        vision_models = [m for m in models if any(
            kw in m.lower() for kw in ["llava", "bakllava", "minicpm",
                                        "llama3.2-vision", "gemma3",
                                        "moondream", "cogvlm"]
        )]
        if vision_models:
            return {"model": vision_models[0], "all_models": models}
        # No vision model — need to pull one
        return {"model": None, "status": "no_vision_model",
                "ollama_bin": ollama_bin, "all_models": models}
    except Exception:
        return {"model": None, "status": "server_not_running",
                "ollama_bin": ollama_bin}


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python analyze_image.py --provider <provider> --image <path> --prompt <text> [--model <model>] [--api-key <key>]")
        print()
        print("Providers:")
        print("  openrouter  — OpenRouter API (needs OPENROUTER_API_KEY or --api-key)")
        print("  ollama      — Local Ollama (needs ollama installed + vision model)")
        print()
        print("Options:")
        print("  --provider   Provider to use (required)")
        print("  --image      Path to image file (required)")
        print("  --prompt     Text prompt describing what to analyze (required)")
        print("  --model      Override default model")
        print("  --api-key    API key for OpenRouter (overrides env var)")
        print()
        print("Examples:")
        print("  python analyze_image.py --provider openrouter --image screenshot.png --prompt 'Describe this image'")
        print("  python analyze_image.py --provider ollama --image photo.jpg --model llava:13b --prompt 'What is in this photo?'")
        sys.exit(0)

    provider = None
    image_path = None
    prompt = "Describe this image in detail."
    model = None
    api_key = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--provider" and i + 1 < len(args):
            provider = args[i + 1]; i += 2
        elif args[i] == "--image" and i + 1 < len(args):
            image_path = args[i + 1]; i += 2
        elif args[i] == "--prompt" and i + 1 < len(args):
            prompt = args[i + 1]; i += 2
        elif args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]; i += 2
        elif args[i] == "--api-key" and i + 1 < len(args):
            api_key = args[i + 1]; i += 2
        else:
            i += 1

    if not provider or not image_path:
        print("Error: --provider and --image are required. Use --help for usage.", file=sys.stderr)
        sys.exit(1)

    if not Path(image_path).is_file():
        print(f"Error: image file not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    if provider == "openrouter":
        key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            print("Error: OpenRouter API key not found. Set OPENROUTER_API_KEY or pass --api-key.", file=sys.stderr)
            sys.exit(1)
        result = analyze_openrouter(image_path, prompt, key,
                                    model or OR_DEFAULT_MODEL)
    elif provider == "ollama":
        result = analyze_ollama(image_path, prompt,
                                model or OLLAMA_DEFAULT_MODEL)
    else:
        print(f"Error: unknown provider '{provider}'. Use 'openrouter' or 'ollama'.", file=sys.stderr)
        sys.exit(1)

    print(result)
    sys.exit(0 if not result.startswith(("Error", "OpenRouter error", "Ollama error", "Ollama request", "OpenRouter request")) else 1)


if __name__ == "__main__":
    main()
