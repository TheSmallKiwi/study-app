# Study App

A typing-based micro-learning tool built with Python and tkinter. Symbols are displayed one at a time — type out the name and description to advance. Characters highlight green or red as you type, and periodic quizzes test recall.

![Python](https://img.shields.io/badge/Python-3.10+-blue)

## Features

- **Type-to-learn** — see a symbol, type its name and description to reinforce memory
- **Live feedback** — characters turn green (correct) or red (incorrect) as you type
- **Weighted repetition** — items you get right in quizzes appear less often over time
- **Periodic quizzes** — every few items, a quiz tests recall (type the name from memory)
- **Progress tracking** — saved per-topic in `progress/`

## Included Topics

| Topic | File | Items |
|---|---|---|
| Greek Letters in Research | `topics/greek_letters.json` | 30 letters with their meanings in math, physics, ML, and statistics |
| Phonetic Alphabet (IPA) | `topics/phonetic_alphabet.json` | 30 IPA symbols with pronunciations and example words |

## Usage

```
pythonw study_app.py [topic_name]
```

Or on Windows, use the launch script:

```
start.cmd [topic_name]
```

If no topic is specified, it defaults to `greek_letters`.

**Controls:**
- Type to match the displayed text
- `Backspace` to undo a character
- `Esc` to quit

## Adding a Topic

Create a JSON file in `topics/` with this structure:

```json
{
  "title": "Topic Title",
  "description": "Short description",
  "items": [
    {
      "symbol": "X",
      "name": "name",
      "description": "what to learn"
    }
  ]
}
```

The app will automatically pick it up when you pass the filename (without `.json`) as the topic argument.

## Requirements

- Python 3.10+
- tkinter (included with most Python installations)
