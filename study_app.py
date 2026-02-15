"""
Study App - A typing-based micro learning tool (tkinter GUI).

Displays study items one at a time. Type what you see to advance.
Characters turn green (correct) or red (incorrect) as you type.
The app watches for a .stop file and exits automatically when found.

Usage:
    pythonw study_app.py [topic_name]

Topics are JSON files in the 'topics/' directory.
To add a new topic, create a JSON file with the structure:
{
    "title": "Topic Title",
    "description": "Short description",
    "items": [
        { "symbol": "X", "name": "name", "description": "what to learn" },
        ...
    ]
}
"""

import json
import os
import random
import sys
import tkinter as tk

# ── Paths ──────────────────────────────────────────────────

APP_DIR = os.path.dirname(os.path.abspath(__file__))
TOPICS_DIR = os.path.join(APP_DIR, "topics")
PROGRESS_DIR = os.path.join(APP_DIR, "progress")
STOP_FILE = os.path.join(APP_DIR, ".stop")
LOCK_FILE = os.path.join(APP_DIR, ".lock")

DECAY_FACTOR = 0.7
MIN_WEIGHT = 0.1
QUIZ_INTERVAL = 3

# ── Colors ─────────────────────────────────────────────────

BG = "#1e1e2e"
FG = "#cdd6f4"
CYAN = "#89dceb"
GREEN = "#a6e3a1"
RED = "#f38ba8"
YELLOW = "#f9e2af"
MAUVE = "#cba6f7"
DIM = "#585b70"

# ── Helpers ────────────────────────────────────────────────


def load_topic(name):
    """Load a topic JSON file from the topics directory."""
    path = os.path.join(TOPICS_DIR, f"{name}.json")
    if not os.path.exists(path):
        available = [
            f[:-5] for f in os.listdir(TOPICS_DIR) if f.endswith(".json")
        ]
        msg = f"Topic '{name}' not found."
        if available:
            msg += f"\nAvailable: {', '.join(available)}"
        raise SystemExit(msg)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cleanup_stop_file():
    try:
        if os.path.exists(STOP_FILE):
            os.remove(STOP_FILE)
    except OSError:
        pass


def create_lock():
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))


def remove_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except OSError:
        pass


def load_progress(topic_name):
    os.makedirs(PROGRESS_DIR, exist_ok=True)
    path = os.path.join(PROGRESS_DIR, f"{topic_name}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(topic_name, progress):
    os.makedirs(PROGRESS_DIR, exist_ok=True)
    path = os.path.join(PROGRESS_DIR, f"{topic_name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)


# ── App ────────────────────────────────────────────────────


class StudyApp:
    def __init__(self, topic_name="greek_letters"):
        self.topic_name = topic_name
        self.topic = load_topic(topic_name)
        self.items = self.topic["items"][:]
        self.idx = 0
        self.typed = []
        self.advancing = False
        self.revealed = False
        self.last_item = None

        # ── Progress & quiz state ─────────────────────────────
        self.progress = load_progress(topic_name)
        for item in self.items:
            self.progress.setdefault(item["name"], 1.0)
        self.quiz_mode = False
        self.items_since_quiz = 0

        # ── Window setup ───────────────────────────────────
        self.root = tk.Tk()
        self.root.title(f"Study: {topic_name}")
        self.root.configure(bg=BG)
        self.root.geometry("600x410+1195+915")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # ── Header row ─────────────────────────────────────
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=20, pady=(18, 0))

        self.title_label = tk.Label(
            header, text=self.topic["title"],
            font=("Segoe UI", 11, "bold"), fg=FG, bg=BG, anchor="w"
        )
        self.title_label.pack(side="left")

        self.counter_label = tk.Label(
            header, text="",
            font=("Segoe UI", 11), fg=DIM, bg=BG, anchor="e"
        )
        self.counter_label.pack(side="right")

        # ── Symbol ─────────────────────────────────────────
        self.symbol_label = tk.Label(
            self.root, text="",
            font=("Segoe UI", 72, "bold"), fg=CYAN, bg=BG
        )
        self.symbol_label.pack(expand=True)

        # ── Typing line (Text widget for per-character coloring + word wrap)
        self.typing_text = tk.Text(
            self.root, bg=BG, fg=DIM, font=("Consolas", 16),
            wrap="word", highlightthickness=0, borderwidth=0,
            height=3, padx=10, pady=4, cursor="arrow"
        )
        self.typing_text.pack(fill="x", padx=0, pady=(0, 10))
        self.typing_text.config(state="disabled")
        # Color tags
        self.typing_text.tag_configure("green", foreground=GREEN)
        self.typing_text.tag_configure("red", foreground=RED)
        self.typing_text.tag_configure("yellow", foreground=YELLOW)
        self.typing_text.tag_configure("dim", foreground=DIM)
        self.typing_text.tag_configure("center", justify="center")
        self.typing_text.tag_configure("field", foreground="#7f849c",
                                       font=("Consolas", 8, "italic"))

        # ── Footer ─────────────────────────────────────────
        self.footer_label = tk.Label(
            self.root, text="Esc quit  |  Backspace undo",
            font=("Segoe UI", 9), fg=DIM, bg=BG
        )
        self.footer_label.pack(pady=(0, 14))

        # ── Bindings ───────────────────────────────────────
        self.root.bind("<Key>", self.on_key)
        self.root.focus_force()

        # ── Start ──────────────────────────────────────────
        cleanup_stop_file()
        create_lock()
        self.load_item()
        self.check_stop()

    def pick_item(self):
        weights = [self.progress.get(item["name"], 1.0) for item in self.items]
        while True:
            choice = random.choices(self.items, weights=weights, k=1)[0]
            if choice is not self.last_item or len(self.items) == 1:
                return choice

    def load_item(self):
        self.items_since_quiz += 1
        if self.items_since_quiz > QUIZ_INTERVAL:
            self.items_since_quiz = 0
            self.load_quiz()
            return

        item = self.pick_item()
        self.current_item = item
        self.last_item = item
        self.symbol = item["symbol"]
        self.text = f"{item['name']}: {item['description']}"
        self.typed = []
        self.advancing = False
        self.revealed = False
        self.quiz_mode = False

        self.symbol_label.config(text=self.symbol, fg=CYAN)
        self.counter_label.config(text=f"{self.idx + 1} / {len(self.items)}")
        self.idx += 1

        self._clear_typing_area()
        self.root.after(1000, self.reveal_text)

    def load_quiz(self):
        item = self.pick_item()
        self.current_item = item
        self.last_item = item
        self.symbol = item["symbol"]
        self.text = item["name"]
        self.typed = []
        self.advancing = False
        self.revealed = False
        self.quiz_mode = True

        self.symbol_label.config(text=self.symbol, fg=MAUVE)
        self.counter_label.config(text="Quiz")

        self._clear_typing_area()
        self.root.after(1000, self.reveal_text)

    def _clear_typing_area(self):
        t = self.typing_text
        t.config(state="normal")
        t.delete("1.0", "end")
        t.config(state="disabled")

    def reveal_text(self):
        self.revealed = True
        self.render_typing()

    def build_field_line(self):
        """Build a line with field labels centered under their terms."""
        item = self.current_item
        field_str = item.get("field", "")
        if not field_str:
            return ""

        terms = [t.strip() for t in item["description"].split(",")]
        fields = [f.strip() for f in field_str.split(",")]

        line = [" "] * len(self.text)
        search_from = len(item["name"]) + 2  # after "name: "

        for i, term in enumerate(terms):
            if i >= len(fields):
                break
            pos = self.text.find(term, search_from)
            if pos == -1:
                continue
            center = pos + len(term) // 2
            fld = fields[i]
            start = max(0, center - len(fld) // 2)
            for j, ch in enumerate(fld):
                if start + j < len(line):
                    line[start + j] = ch
            search_from = pos + len(term)

        return "".join(line)

    def render_typing(self):
        t = self.typing_text
        t.config(state="normal")
        t.delete("1.0", "end")

        if self.quiz_mode:
            for i, ch in enumerate(self.text):
                if i < len(self.typed):
                    tag = "green" if self.typed[i] == ch else "red"
                    t.insert("end", self.typed[i], (tag, "center"))
                elif i == len(self.typed):
                    t.insert("end", "_", ("yellow", "center"))
                else:
                    t.insert("end", "_", ("dim", "center"))
        else:
            for i, ch in enumerate(self.text):
                if i < len(self.typed):
                    tag = "green" if self.typed[i] == ch else "red"
                elif i == len(self.typed):
                    tag = "yellow"
                else:
                    tag = "dim"
                t.insert("end", ch, (tag, "center"))

            field_line = self.build_field_line()
            if field_line:
                t.insert("end", "\n" + field_line, ("field", "center"))

        t.config(state="disabled")

    def on_key(self, event):
        if event.keysym == "Escape":
            self.on_close()
            return

        if self.advancing or not self.revealed:
            return

        if event.keysym == "BackSpace":
            if self.typed:
                self.typed.pop()
                self.render_typing()
            return

        # Ignore non-printable / modifier keys
        ch = event.char
        if not ch or ord(ch) < 32:
            return

        self.typed.append(ch)
        self.render_typing()

        if len(self.typed) == len(self.text):
            self.advancing = True
            if self.quiz_mode:
                self.finish_quiz()
            else:
                self.root.after(400, self.advance)

    def finish_quiz(self):
        correct = all(
            self.typed[i] == self.text[i] for i in range(len(self.text))
        )
        if correct:
            name = self.current_item["name"]
            self.progress[name] = max(
                MIN_WEIGHT, self.progress.get(name, 1.0) * DECAY_FACTOR
            )
            save_progress(self.topic_name, self.progress)
            self.symbol_label.config(fg=GREEN)
            self.root.after(800, self.advance)
        else:
            self.symbol_label.config(fg=RED)
            t = self.typing_text
            t.config(state="normal")
            t.delete("1.0", "end")
            t.insert("end", self.text, ("green", "center"))
            t.config(state="disabled")
            self.root.after(2000, self.advance)

    def advance(self):
        self.load_item()

    def check_stop(self):
        if os.path.exists(STOP_FILE):
            self.on_close()
            return
        self.root.after(500, self.check_stop)

    def on_close(self):
        cleanup_stop_file()
        remove_lock()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "greek_letters"
    app = StudyApp(topic)
    app.run()
