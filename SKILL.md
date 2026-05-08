---
name: read-image
description: Use when the user asks to "read screenshot", "describe image", "read image", "что на скриншоте", "прочитай скрин", "анализируй изображение", or any time the user wants to analyze an image/screenshot they pasted. This skill auto-detects the IDE (OpenCode, Claude Code, Cursor), extracts images from the chat database, and analyzes them via MiniMax, OpenRouter, Ollama, or native multimodal — automatically selecting the best available provider. If no provider is configured, the skill guides the user through setup step by step.
---

# read-image

Extracts images from the IDE's chat database and analyzes them using the best available vision provider. Supports OpenCode, Claude Code, and Cursor for extraction. Supports MiniMax MCP, OpenRouter, Ollama, and native multimodal for analysis.

If no provider is configured — guides the user through setup interactively.

## Quick start

```bash
python3 scripts/extract_images.py
```

Output:

```json
{"ide": "opencode", "count": 2, "images": [{"index": 1, "path": "...", ...}, ...]}
```

## Supported IDEs

| IDE | Detection | Extraction backend |
|-----|-----------|--------------------|
| **OpenCode** | `OPENCODE=1` + `~/.local/share/opencode/opencode.db` | SQLite `part` table |
| **Claude Code** | `CLAUDE_CODE_*` + `~/.claude/projects/*.jsonl` | Session JSONL |
| **Cursor** | `~/.cursor/` or `~/Library/Application Support/Cursor/` | `state.vscdb` agentKv blobs |

---

# Provider Detection & Routing

**This is the most important section.** Before analyzing any image, determine which vision provider to use.

## Provider priority (check in this order)

| # | Provider | How to detect | Action |
|---|----------|--------------|--------|
| 1 | **MiniMax MCP** | The `MiniMax_understand_image` tool is available in your tool list | Use it directly — no setup needed |
| 2 | **OpenRouter** | `echo $OPENROUTER_API_KEY` returns a non-empty value | Use `python3 scripts/analyze_image.py --provider openrouter --image <path> --prompt "..."` |
| 3 | **Ollama** | Run `python3 scripts/analyze_image.py` with `--provider ollama` or check `which ollama` + `ollama list` | Use `python3 scripts/analyze_image.py --provider ollama --image <path> --prompt "..."` |
| 4 | **Native multimodal** | You are a multimodal model (Claude, GPT-4o, Gemini) and can "see" images in context | Describe the image directly — no extraction needed for in-context images |
| 5 | **Nothing configured** | None of the above | Run the **Setup Wizard** below |

## How to check providers

Do this BEFORE extracting images if you suspect the user doesn't have MiniMax:

```
1. Check tool list: is MiniMax_understand_image available? → Yes: skip to extraction, use MiniMax
2. Run: echo $OPENROUTER_API_KEY → non-empty: OpenRouter available
3. Run: which ollama && ollama list 2>/dev/null → has vision model: Ollama available
4. Are you Claude/GPT-4o? → Yes: native multimodal available (describe directly)
5. None of the above → Run Setup Wizard
```

---

# Workflow

## Full flow

```
User: "прочитай скриншот"
     │
     ├─ 1. Check providers (see Provider Detection above)
     │     └─ Nothing configured? → Run Setup Wizard, stop here
     │
     ├─ 2. Extract images: python3 scripts/extract_images.py
     │     └─ Error? → Tell user "No images found", stop here
     │
     ├─ 3. Analyze each image with the detected provider
     │     ├─ MiniMax: call MiniMax_understand_image tool
     │     ├─ OpenRouter: python3 scripts/analyze_image.py --provider openrouter --image <path>
     │     ├─ Ollama: python3 scripts/analyze_image.py --provider ollama --image <path>
     │     └─ Native: describe directly
     │
     └─ 4. Return results to user
```

## Step 1: Ensure a provider is available

Before extracting, verify at least one provider is configured. If not — run the setup wizard. Do NOT leave the user without a working provider.

## Step 2: Extract images

```bash
python3 scripts/extract_images.py
# or
python3 scripts/extract_images.py --last 5
```

## Step 3: Analyze

### MiniMax

For each image, call `MiniMax_understand_image`:

```
prompt: "Describe this image in detail. What does it show? Read all text visible on the screen. Describe the interface, code, and any visible elements."
image_source: <path>
```

### OpenRouter

```bash
python3 scripts/analyze_image.py \
  --provider openrouter \
  --image <path> \
  --prompt "Describe this image in detail. Read all visible text. Describe the interface and code."
```

Default model: `google/gemini-2.5-flash` (cheap, fast, good vision).
Override: `--model qwen/qwen2.5-vl-72b-instruct` for better quality.

### Ollama

```bash
python3 scripts/analyze_image.py \
  --provider ollama \
  --image <path> \
  --prompt "Describe this image in detail. Read all visible text."
```

Default model: `llava:13b`. Override with `--model <model>`.

### Native multimodal

If you (the model) are Claude/GPT-4o and the images are in your context — describe them directly. This is the fallback when no other provider is available and the user hasn't completed setup yet.

## Step 4: Return results

- **Single image**: return the analysis directly
- **Multiple images**: describe each separately (Image 1, Image 2, ...) + summary if related

---

# Setup Wizard

When the user has NO provider configured, you MUST guide them through setup. Be conversational, friendly, and concrete. Never just say "configure a provider" — give exact commands.

## Wizard flow

### Phase 1: Diagnose

Tell the user what's happening:

> Чтобы читать изображения, мне нужен vision-провайдер. Давай проверим, что у тебя есть...

Check all providers silently (MiniMax tool, `$OPENROUTER_API_KEY`, `which ollama`).

### Phase 2: Offer options

If nothing is configured, present the two fastest options:

> У тебя пока нет настроенных vision-провайдеров. Вот что можно поставить быстрее всего:
>
> **1. OpenRouter** — быстрее всего, ~2 минуты
>    • Регистрируешься на [openrouter.ai](https://openrouter.ai) (Google/GitHub вход)
>    • В Settings → Keys создаёшь API-ключ
>    • Говоришь мне ключ, я сохраняю
>    • Pay-as-you-go, большинство моделей от $0
>
> **2. Ollama** — полностью локально, ~5 минут
>    • `brew install ollama` (или скачай с [ollama.com](https://ollama.com))
>    • `ollama pull llava:13b`
>    • Всё работает без интернета, полностью бесплатно
>
> Какой вариант выберешь? (1 — OpenRouter, 2 — Ollama)

### Phase 3: Guided setup

#### If user chooses OpenRouter:

> Отлично! Сделай так:
>
> 1. Открой [openrouter.ai](https://openrouter.ai) в браузере
> 2. Нажми **Sign Up** (можно через Google или GitHub)
> 3. После входа открой [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys)
> 4. Нажми **Create Key** — скопируй ключ
> 5. Вернись сюда и скажи мне ключ. Я сохраню его в `~/.openrouter/api_key`
>
> *(Жду ключ...)*

When user gives the key, save it:

```bash
mkdir -p ~/.openrouter && echo "sk-or-v1-..." > ~/.openrouter/api_key && chmod 600 ~/.openrouter/api_key
```

Also export it for the current session:
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

Then verify:

> Готово! Давай проверим — я сейчас прочитаю твою картинку через OpenRouter...

Proceed to Step 3 (Analyze).

#### If user chooses Ollama:

> Отлично! Выполни эти команды по очереди:
>
> **Шаг 1 — установка Ollama:**
> ```bash
> brew install ollama
> ```
> Если у тебя не Mac — скачай с [ollama.com](https://ollama.com)
>
> **Шаг 2 — запуск сервера:**
> ```bash
> ollama serve
> ```
>
> **Шаг 3 — скачивание vision-модели:**
> ```bash
> ollama pull llava:13b
> ```
> Это займёт пару минут (модель ~8GB).
>
> Когда будет готово, скажи мне "готово" — я проверю и прочитаю картинку.

When user says "готово", verify:

```bash
which ollama && ollama list
```

Then proceed to Step 3 (Analyze).

### Phase 4: Fallback if user refuses both

> Без провайдера я не смогу анализировать изображения из базы чата.
>
> Если хочешь — я могу попробовать прочитать картинку напрямую (если у меня есть multimodal-доступ). Или вернись к настройке позже — скажи "настрой провайдер".

### Phase 5: Already configured, just missing for current session

If user says "у меня есть ключ OpenRouter, я его вводил раньше":

```bash
export OPENROUTER_API_KEY=$(cat ~/.openrouter/api_key 2>/dev/null)
```

---

# Multi-image example

User pastes 3 screenshots in one message:

1. Check providers → MiniMax available
2. Run `python3 scripts/extract_images.py` → returns 3 images
3. Call `MiniMax_understand_image` for each (in parallel if possible)
4. Present:
   ```
   **Image 1:** [description]
   **Image 2:** [description]
   **Image 3:** [description]
   Summary: [if images are related]
   ```

---

# IDE-specific extraction details

## Claude Code

Session data in `~/.claude/projects/<project>/<session-id>.jsonl`. Extraction:

1. Finds the most recently modified session JSONL
2. Scans backwards for the latest user message with `type: "image"` content
3. Extracts all images from that message (handles multi-image)
4. Decodes base64 and saves to disk

## Cursor

Chat images in `state.vscdb` → `cursorDiskKV` → `agentKv:blob:*`.

Two formats:
1. **Base64**: `data:image/png;base64,iVBORw0KGgo...`
2. **Hex**: `{"type":"image","image":{"__type":"Uint8Array","hex":"ffd8ffe0..."}}`

Extraction uses `rowid DESC` for chronological ordering.

DB paths:
- macOS: `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`
- Linux: `~/.config/Cursor/User/globalStorage/state.vscdb`

## OpenCode

Images in `~/.local/share/opencode/opencode.db` → `part` table. Extracts all image parts from the most recent message.

---

# Common mistakes

- **Calling MiniMax without checking availability**: always check if the tool exists first. If not → fall back to OpenRouter/Ollama/Setup Wizard.
- **Leaving user without a provider**: if nothing is configured, you MUST run the Setup Wizard. Do not just say "install something" — give exact commands and wait for user response.
- **Wrong working directory**: always run scripts from the skill root (`read-image/`).
- **Skipping JSON parsing**: always parse `extract_images.py` output properly. Do not grep/sed.
- **Assuming single image**: always check `count` in the JSON output.
- **Wrong path for analysis**: use the `path` field from extraction JSON directly — do not construct paths manually.
- **Forgetting to export API key**: after saving to `~/.openrouter/api_key`, also `export OPENROUTER_API_KEY` for the current session.
