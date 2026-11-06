"""A graphical Hangman game with an animated gallows."""

import random
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

MAX_MISTAKES = 6
KEY_ROWS = ("QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM")

BACKGROUND = "#0f172a"
PANEL = "#1e293b"
PANEL_LIGHT = "#273449"
TEXT = "#f8fafc"
MUTED = "#94a3b8"
ACCENT = "#38bdf8"
GOOD = "#4ade80"
BAD = "#fb7185"


def load_words(word_file: Path | None = None) -> list[str]:
    """Load playable words from the words.txt file next to this script."""
    if word_file is None:
        word_file = Path(__file__).with_name("words.txt")

    words = [
        line.strip().lower()
        for line in word_file.read_text(encoding="utf-8-sig").splitlines()
        if line.strip().isalpha() and len(line.strip()) > 1
    ]
    if not words:
        raise ValueError(f"No playable words found in {word_file}")
    return words


def display_word(word: str, guessed_letters: set[str]) -> str:
    """Return the word with unguessed letters masked."""
    return " ".join(
        letter.upper() if letter in guessed_letters else "_"
        for letter in word
    )


class HangmanApp:
    """Manage the graphical game and its animated drawing."""

    def __init__(self, root: tk.Tk, words: list[str]) -> None:
        self.root = root
        self.words = words
        self.secret_word = ""
        self.guessed_letters: set[str] = set()
        self.mistakes = 0
        self.finished = False
        self.animating = False
        self.animation_job: str | None = None
        self.round_id = 0
        self.letter_buttons: dict[str, tk.Button] = {}

        root.title("Hangman")
        root.configure(bg=BACKGROUND)
        root.geometry("1000x720")
        root.minsize(860, 650)

        self._build_interface()
        root.bind("<KeyPress>", self._on_keypress)
        self.new_game()

    def _build_interface(self) -> None:
        container = tk.Frame(self.root, bg=BACKGROUND, padx=30, pady=22)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(1, weight=1)

        header = tk.Frame(container, bg=BACKGROUND)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        tk.Label(
            header,
            text="HANGMAN",
            font=("Segoe UI", 26, "bold"),
            fg=TEXT,
            bg=BACKGROUND,
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Guess the hidden word before the drawing is complete.",
            font=("Segoe UI", 11),
            fg=MUTED,
            bg=BACKGROUND,
        ).pack(anchor="w", pady=(3, 0))

        art_panel = tk.Frame(container, bg=PANEL, padx=18, pady=18)
        art_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        art_panel.rowconfigure(0, weight=1)
        art_panel.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            art_panel,
            bg=PANEL,
            highlightthickness=0,
            width=400,
            height=390,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self._draw_gallows)

        self.mistakes_label = tk.Label(
            art_panel,
            text="Mistakes: 0 / 6",
            font=("Segoe UI", 12, "bold"),
            fg=MUTED,
            bg=PANEL,
        )
        self.mistakes_label.grid(row=1, column=0, pady=(10, 0))

        game_panel = tk.Frame(container, bg=PANEL, padx=22, pady=22)
        game_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        game_panel.columnconfigure(0, weight=1)

        tk.Label(
            game_panel,
            text="YOUR WORD",
            font=("Segoe UI", 10, "bold"),
            fg=MUTED,
            bg=PANEL,
        ).grid(row=0, column=0, sticky="w")

        self.word_label = tk.Label(
            game_panel,
            text="",
            font=("Consolas", 23, "bold"),
            fg=TEXT,
            bg=PANEL,
            pady=16,
            wraplength=460,
        )
        self.word_label.grid(row=1, column=0, sticky="w")

        self.status_label = tk.Label(
            game_panel,
            text="Choose a letter to begin.",
            font=("Segoe UI", 11),
            fg=ACCENT,
            bg=PANEL,
            anchor="w",
            wraplength=440,
        )
        self.status_label.grid(row=2, column=0, sticky="ew", pady=(0, 18))

        tk.Label(
            game_panel,
            text="GUESSED LETTERS",
            font=("Segoe UI", 9, "bold"),
            fg=MUTED,
            bg=PANEL,
        ).grid(row=3, column=0, sticky="w")
        self.guessed_label = tk.Label(
            game_panel,
            text="None yet",
            font=("Segoe UI", 11),
            fg=TEXT,
            bg=PANEL,
            anchor="w",
        )
        self.guessed_label.grid(row=4, column=0, sticky="ew", pady=(5, 18))

        keyboard = tk.Frame(game_panel, bg=PANEL)
        keyboard.grid(row=5, column=0, sticky="ew")
        for row_index, row_letters in enumerate(KEY_ROWS):
            row_frame = tk.Frame(keyboard, bg=PANEL)
            row_frame.pack(pady=4)
            for letter in row_letters:
                button = tk.Button(
                    row_frame,
                    text=letter,
                    width=3,
                    height=1,
                    font=("Segoe UI", 10, "bold"),
                    fg=TEXT,
                    bg=PANEL_LIGHT,
                    activeforeground=TEXT,
                    activebackground="#334155",
                    disabledforeground="#64748b",
                    relief="flat",
                    bd=0,
                    cursor="hand2",
                    command=lambda picked=letter: self.guess(picked.lower()),
                )
                button.pack(side="left", padx=3)
                self.letter_buttons[letter.lower()] = button

        self.new_game_button = tk.Button(
            game_panel,
            text="New word",
            font=("Segoe UI", 11, "bold"),
            fg=BACKGROUND,
            bg=ACCENT,
            activeforeground=BACKGROUND,
            activebackground="#7dd3fc",
            relief="flat",
            bd=0,
            padx=18,
            pady=9,
            cursor="hand2",
            command=self.new_game,
        )
        self.new_game_button.grid(row=6, column=0, sticky="ew", pady=(20, 0))

    def new_game(self) -> None:
        """Start a fresh round and cancel any unfinished animation."""
        self.round_id += 1
        if self.animation_job is not None:
            self.root.after_cancel(self.animation_job)
            self.animation_job = None

        self.secret_word = random.choice(self.words)
        self.guessed_letters.clear()
        self.mistakes = 0
        self.finished = False
        self.animating = False
        self._update_display()
        self.status_label.configure(
            text="Choose a letter to begin.",
            fg=ACCENT,
        )
        self._set_keyboard_enabled(True)
        self._draw_gallows()

    def guess(self, letter: str) -> None:
        """Apply one letter guess and update the game state."""
        if self.finished or self.animating or letter in self.guessed_letters:
            return

        self.guessed_letters.add(letter)
        self.letter_buttons[letter].configure(state="disabled")
        self._update_display()

        if letter in self.secret_word:
            self.status_label.configure(
                text=f"Nice! {letter.upper()} is in the word.",
                fg=GOOD,
            )
            if all(char in self.guessed_letters for char in self.secret_word):
                self._finish_game(won=True)
            return

        self.mistakes += 1
        self.mistakes_label.configure(
            text=f"Mistakes: {self.mistakes} / {MAX_MISTAKES}",
            fg=BAD if self.mistakes >= 4 else MUTED,
        )
        self.status_label.configure(
            text=f"{letter.upper()} is not in the word.",
            fg=BAD,
        )
        self._animate_mistake()

    def _animate_mistake(self) -> None:
        """Draw the next figure part in short steps."""
        self.animating = True
        self._set_keyboard_enabled(False)
        current_round = self.round_id
        part = self.mistakes - 1
        steps = 8

        def animate(step: int) -> None:
            if current_round != self.round_id:
                return
            self._draw_gallows(partial_part=part, progress=step / steps)
            if step < steps:
                self.animation_job = self.root.after(22, animate, step + 1)
                return

            self.animation_job = None
            self.animating = False
            if self.mistakes == MAX_MISTAKES:
                self._finish_game(won=False)
            else:
                self._set_keyboard_enabled(True)

        animate(1)

    def _finish_game(self, won: bool) -> None:
        """Show the round result and prevent further guesses."""
        self.finished = True
        self._set_keyboard_enabled(False)
        if won:
            self.status_label.configure(
                text=f"You got it! The word was {self.secret_word.upper()}.",
                fg=GOOD,
            )
        else:
            self.status_label.configure(
                text=f"Game over! The word was {self.secret_word.upper()}.",
                fg=BAD,
            )
            self._draw_gallows()

    def _update_display(self) -> None:
        self.word_label.configure(
            text=display_word(self.secret_word, self.guessed_letters)
        )
        self.guessed_label.configure(
            text=", ".join(letter.upper() for letter in sorted(self.guessed_letters))
            or "None yet"
        )
        self.mistakes_label.configure(
            text=f"Mistakes: {self.mistakes} / {MAX_MISTAKES}",
            fg=MUTED,
        )

    def _set_keyboard_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for button in self.letter_buttons.values():
            if button["text"].lower() not in self.guessed_letters:
                button.configure(state=state)

    def _on_keypress(self, event: tk.Event) -> None:
        letter = event.char.lower()
        if len(letter) == 1 and letter.isascii() and letter.isalpha():
            self.guess(letter)

    def _draw_gallows(
        self,
        _event: tk.Event | None = None,
        partial_part: int | None = None,
        progress: float = 1.0,
    ) -> None:
        """Redraw the scaffold and the currently visible figure parts."""
        if not hasattr(self, "canvas"):
            return

        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 360)
        height = max(self.canvas.winfo_height(), 340)
        left = width * 0.18
        base_y = height * 0.83
        top_y = height * 0.12
        beam_x = width * 0.72
        head_x = beam_x
        head_y = height * 0.32
        head_radius = min(width, height) * 0.075
        color = "#cbd5e1"
        line_width = 5

        self.canvas.create_line(
            left, base_y, width * 0.84, base_y, fill=color, width=line_width
        )
        self.canvas.create_line(
            left + width * 0.1, base_y, left + width * 0.1, top_y,
            fill=color, width=line_width,
        )
        self.canvas.create_line(
            left + width * 0.1, top_y, beam_x, top_y,
            fill=color, width=line_width,
        )
        self.canvas.create_line(
            beam_x, top_y, beam_x, head_y - head_radius,
            fill=color, width=line_width,
        )

        body_parts = (
            ("head", None),
            ("line", (head_x, head_y + head_radius, head_x, height * 0.62)),
            ("line", (head_x, height * 0.43, head_x - width * 0.12, height * 0.53)),
            ("line", (head_x, height * 0.43, head_x + width * 0.12, height * 0.53)),
            ("line", (head_x, height * 0.62, head_x - width * 0.11, height * 0.76)),
            ("line", (head_x, height * 0.62, head_x + width * 0.11, height * 0.76)),
        )
        visible_parts = min(self.mistakes, len(body_parts))

        for index, (part_type, coordinates) in enumerate(body_parts):
            if index >= visible_parts:
                break
            fraction = progress if index == partial_part else 1.0
            if part_type == "head":
                radius = head_radius * fraction
                self.canvas.create_oval(
                    head_x - radius,
                    head_y - radius,
                    head_x + radius,
                    head_y + radius,
                    outline=BAD,
                    width=4,
                )
            else:
                start_x, start_y, end_x, end_y = coordinates
                self.canvas.create_line(
                    start_x,
                    start_y,
                    start_x + (end_x - start_x) * fraction,
                    start_y + (end_y - start_y) * fraction,
                    fill=BAD,
                    width=4,
                    capstyle="round",
                )

        is_final_loss = self.finished and self.mistakes == MAX_MISTAKES
        if is_final_loss:
            mouth_width = width * 0.075
            self.canvas.create_arc(
                head_x - mouth_width,
                head_y + head_radius * 0.05,
                head_x + mouth_width,
                head_y + head_radius * 0.8,
                start=205,
                extent=130,
                style="arc",
                outline=BAD,
                width=3,
            )

        if is_final_loss:
            eye_offset = head_radius * 0.38
            eye_size = head_radius * 0.19
            for eye_x in (head_x - eye_offset, head_x + eye_offset):
                self.canvas.create_line(
                    eye_x - eye_size,
                    head_y - eye_offset - eye_size,
                    eye_x + eye_size,
                    head_y - eye_offset + eye_size,
                    fill=BAD,
                    width=3,
                )
                self.canvas.create_line(
                    eye_x - eye_size,
                    head_y - eye_offset + eye_size,
                    eye_x + eye_size,
                    head_y - eye_offset - eye_size,
                    fill=BAD,
                    width=3,
                )
            self.canvas.create_text(
                head_x + width * 0.17,
                height * 0.74,
                text="RIP",
                fill=BAD,
                font=("Segoe UI", 13, "bold"),
            )


def main() -> None:
    """Load the word list and launch the desktop game."""
    root = tk.Tk()
    try:
        words = load_words()
    except (OSError, ValueError) as error:
        root.withdraw()
        messagebox.showerror("Unable to start Hangman", str(error), parent=root)
        root.destroy()
        return

    HangmanApp(root, words)
    root.mainloop()


if __name__ == "__main__":
    main()
