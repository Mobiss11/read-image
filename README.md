# read-image

> 📸 **Скриншоты и изображения из чата — анализ одним движением.**
>
> Скилл сам достанет картинки из базы чата (даже несколько в одном сообщении) и прочитает их через любой vision-провайдер: MiniMax, OpenRouter, Ollama, или нативный multimodal. Если провайдера нет — проведёт за руку через настройку.

---

## ⚡ Установка скилла к ИИ-ассистенту (60 секунд)

Скилл подключается **к твоему ИИ-ассистенту** (OpenCode, Claude Code, Cursor и т.д.) и даёт ему возможность читать скриншоты, которые ты вставил в чат. Без скилла нейронка не видит картинки из истории чата. Со скиллом — извлекает и анализирует.

### Вариант 1 — OpenCode (рекомендую)

```bash
git clone https://github.com/Mobiss11/read-image.git ~/.config/opencode/skills/read-image
```

Готово. Теперь вставь скриншот в чат и скажи:

> прочитай скриншот

Скилл сам определит что ты в OpenCode, достанет картинку из базы, и прочитает.

### Вариант 2 — Claude Code

```bash
git clone https://github.com/Mobiss11/read-image.git ~/.claude/skills/read-image
```

Перезапусти Claude Code. Теперь спроси:

> прочитай скриншот

Claude найдёт скилл, извлечёт картинку из сессии, и проанализирует.

### Вариант 3 — Cursor

Скопируй папку куда угодно, или:

```bash
git clone https://github.com/Mobiss11/read-image.git ~/.cursor/skills/read-image
```

В Cursor: Settings → Features → Skills → Add folder → укажи `~/.cursor/skills/read-image`.

### Вариант 4 — ChatGPT (Custom GPT) / Claude.ai (Project)

1. Скачай ZIP: https://github.com/Mobiss11/read-image/archive/refs/heads/main.zip
2. Залей в Knowledge: `SKILL.md` + всё содержимое `scripts/`
3. В инструкцию Custom GPT добавь:
   > Когда пользователь просит прочитать скриншот/изображение — сначала ищи `SKILL.md` в knowledge, затем выполняй инструкции из него.

### Вариант 5 — Любой другой AI (generic)

Дай нейронке ссылку на этот файл:

> Прочитай https://github.com/Mobiss11/read-image/blob/main/SKILL.md и следуй инструкциям когда я попрошу прочитать скриншот.

---

## ✅ Проверь что AI видит скилл

Вставь скриншот в чат и спроси:

> прочитай скриншот

**Правильный ответ:** нейронка запустит `python3 scripts/extract_images.py`, найдёт картинку, и опишет что на ней. Если отвечает "я не вижу изображений" или "отправь файл" — скилл не подцепился, проверь установку.

---

## 🎯 Что умеет

- **3 IDE** — OpenCode, Claude Code, Cursor. Сам определит где запущен и откуда доставать картинки.
- **Несколько скриншотов** — вставил 3 штуки в одно сообщение? Прочитает все.
- **4 провайдера** — сам выберет лучший из доступных:

| # | Провайдер | Что нужно | Скорость настройки |
|---|-----------|-----------|-------------------|
| 1 | **MiniMax MCP** | Ничего (встроен в OpenCode) | 0 сек |
| 2 | **OpenRouter** | Бесплатный ключ с [openrouter.ai](https://openrouter.ai) | ~2 мин |
| 3 | **Ollama** | `brew install ollama && ollama pull llava:13b` | ~5 мин |
| 4 | **Нативный multimodal** | Ничего (Claude/GPT сами видят картинки) | 0 сек |

- **Setup Wizard** — если ни один провайдер не настроен, скилл сам предложит варианты и шаг за шагом проведёт через установку. Не надо гуглить — всё в диалоге.

---

## 🛠️ Быстрый старт без ИИ-ассистента

Если хочешь просто прочитать скриншот из базы чата руками:

```bash
# 1. Склонируй
git clone https://github.com/Mobiss11/read-image.git
cd read-image

# 2. Достань картинки
python3 scripts/extract_images.py
# → JSON с путями к файлам

# 3. Прочитай (нужен один из провайдеров)
python3 scripts/analyze_image.py --provider openrouter --image <путь> --prompt "Что на скриншоте?"
# или
python3 scripts/analyze_image.py --provider ollama --image <путь> --prompt "Опиши изображение"
```

---

## 📦 Зависимости

- **Python 3.10+**
- Для OpenRouter: бесплатный ключ с [openrouter.ai](https://openrouter.ai)
- Для Ollama: [ollama.com](https://ollama.com) + `ollama pull llava:13b`

Всё остальное встроено в стандартную библиотеку Python (sqlite3, json, urllib).

---

## 📁 Структура

```
read-image/
├── SKILL.md                 ← главный файл (AI читает его)
├── README.md                ← ты здесь
└── scripts/
    ├── extract_images.py    ← достаёт картинки из OpenCode / Claude Code / Cursor
    └── analyze_image.py     ← читает картинки через OpenRouter / Ollama
```

Никаких pip install, виртуальных окружений, или конфигов. Просто склонировал — и работает.

---

## 💬 Примеры запросов

Скилл активируется на эти фразы (и им подобные):

| По-русски | По-английски |
|-----------|-------------|
| *прочитай скриншот* | *read screenshot* |
| *что на скриншоте* | *what's on the screenshot* |
| *анализируй изображение* | *describe image* |
| *опиши картинку* | *read image* |
| *что за ошибка на скрине* | *what does this image show* |

---

## 🔧 Провайдеры подробнее

### OpenRouter (~2 минуты настройки)

1. Иди на [openrouter.ai](https://openrouter.ai) → Sign Up (Google/GitHub)
2. [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) → Create Key
3. Сохрани ключ:
   ```bash
   mkdir -p ~/.openrouter && echo "sk-or-v1-..." > ~/.openrouter/api_key && chmod 600 ~/.openrouter/api_key
   ```

Модель по умолчанию: `google/gemini-2.5-flash` (быстрая, дешёвая, хорошее зрение). Можно переопределить: `--model qwen/qwen2.5-vl-72b-instruct`.

### Ollama (~5 минут, полностью локально)

```bash
brew install ollama        # Mac
# или скачай с ollama.com для Linux/Windows

ollama serve                # запуск сервера (в отдельном терминале)
ollama pull llava:13b      # скачать vision-модель (~8GB)
```

Всё работает без интернета. Бесплатно. Модель можно поменять: `minicpm-v`, `llama3.2-vision`, `gemma3`.

---

## Лицензия

MIT — см. [LICENSE](LICENSE). Делай что хочешь.
