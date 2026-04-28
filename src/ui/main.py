"""Launcher UI - Warm RPG theme with gold accents."""

import contextlib
import pathlib
import threading
from pathlib import Path

import customtkinter as ctk

from src.api import login as api_login
from src.api.mock import AuthResponse
from src.client import launcher as client_launcher
from src import config
from src.zaap.server import ZaapAuth
from tkinter import filedialog, messagebox

# Color system - Warm RPG palette with improved clarity
BG_ROOT = "#4D3E21"
BG_SURFACE = "#6B624F"
BG_CONTENT = "#847C62"
BORDER = "#3b2f19"
ACCENT_START = "#E5CE79"
ACCENT_END = "#AD8343"
TEXT_DARK = "#3b2f19"
TEXT_LIGHT = "#f0f0f0"
TEXT_MUTED = "#a09880"
ERROR = "#c44242"

# Layout constants - Classic launcher size
WINDOW_WIDTH = 640
WINDOW_HEIGHT = 480
PAD_SM = 10
PAD_MD = 14
PAD_LG = 20
ENTRY_WIDTH = 300


class LoginWindow(ctk.CTk):
    """Warm RPG-themed launcher window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Starloco")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.overrideredirect(True)

        ctk.set_appearance_mode("dark")

        self.token: str | None = None
        self.account: str | None = None
        self._show_config = False
        self._client_path = ""
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._zaap = ZaapAuth()

        # Wrapper frame with rounded corners
        self._wrapper = ctk.CTkFrame(
            self,
            fg_color=BG_ROOT,
            corner_radius=8,
            border_color=BORDER,
            border_width=2,
        )
        self._wrapper.pack(fill="both", expand=True)

        try:
            self._zaap.start()
            self._zaap_thread = threading.Thread(target=self._zaap.accept_loop, daemon=True)
            self._zaap_thread.start()
        except Exception as e:
            messagebox.showerror("Zaap Error", f"Failed to start local server: {e}")

        self._build_ui()
        self._load_saved()
        self._load_client_path()
        self.after(100, self._account.focus_set)

    def _build_ui(self) -> None:
        self._build_header()

        self._main_container = ctk.CTkFrame(self._wrapper, fg_color="transparent")
        self._main_container.pack(fill="both", expand=True)

        self._show_login_panel()

    def _build_header(self) -> None:
        """Build the warm golden header bar."""
        header = ctk.CTkFrame(
            self._wrapper,
            fg_color=ACCENT_END,
            height=52,
            corner_radius=0,
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        # Make header draggable since we removed OS title bar
        header.bind("<Button-1>", self._on_drag_start)
        header.bind("<B1-Motion>", self._on_drag_motion)

        ctk.CTkLabel(
            header,
            text="STARLOCO",
            font=("Trebuchet MS", 18, "bold"),
            text_color=TEXT_DARK,
        ).pack(side="left", padx=PAD_LG, pady=PAD_MD)

        right_buttons = ctk.CTkFrame(header, fg_color="transparent")
        right_buttons.pack(side="right", padx=PAD_MD)

        # Close button (packed first - appears rightmost)
        ctk.CTkButton(
            right_buttons,
            text="✕",
            width=36,
            height=36,
            fg_color="transparent",
            text_color=TEXT_DARK,
            hover_color=ERROR,
            border_width=0,
            font=("Trebuchet MS", 14),
            command=self.quit,
        ).pack(side="right", padx=PAD_SM)

        # Settings button (packed second - appears middle)
        ctk.CTkButton(
            right_buttons,
            text="⚙",
            width=36,
            height=36,
            fg_color="transparent",
            text_color=TEXT_DARK,
            hover_color=ACCENT_START,
            border_width=0,
            font=("Trebuchet MS", 16),
            command=self._toggle_config,
        ).pack(side="right", padx=PAD_SM)

        # Minimize button (packed last - appears leftmost)
        ctk.CTkButton(
            right_buttons,
            text="_",
            width=36,
            height=36,
            fg_color="transparent",
            text_color=TEXT_DARK,
            hover_color=BG_CONTENT,
            border_width=0,
            font=("Trebuchet MS", 16),
            command=self.iconify,
        ).pack(side="right", padx=PAD_SM)

    def _on_drag_start(self, event) -> None:
        """Record starting position for window dragging."""
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag_motion(self, event) -> None:
        """Move window based on drag motion."""
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        self.geometry(f"+{self.winfo_x() + dx}+{self.winfo_y() + dy}")

    def _show_login_panel(self) -> None:
        """Show the login panel with username, password, and PLAY button."""
        for child in self._main_container.winfo_children():
            child.destroy()

        card = ctk.CTkFrame(
            self._main_container,
            fg_color=BG_SURFACE,
            corner_radius=8,
            border_color=BORDER,
            border_width=2,
        )
        card.pack(fill="both", expand=True, padx=PAD_LG, pady=PAD_LG)

        # Inner container for vertical + horizontal centering
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True)

        ctk.CTkLabel(
            inner,
            text="Sign in to play",
            font=("Trebuchet MS", 20, "bold"),
            text_color=TEXT_LIGHT,
        ).pack(padx=PAD_LG, pady=(0, PAD_SM))

        self._account = ctk.CTkEntry(
            inner,
            placeholder_text="Username",
            width=ENTRY_WIDTH,
            font=("Trebuchet MS", 13),
            fg_color=BG_CONTENT,
            border_color=BORDER,
            text_color=TEXT_DARK,
            placeholder_text_color=TEXT_MUTED,
        )
        self._account.pack(padx=PAD_LG, pady=(0, PAD_MD))
        self._account.bind("<Return>", lambda _: self._on_login())

        self._password = ctk.CTkEntry(
            inner,
            placeholder_text="Password",
            show="*",
            width=ENTRY_WIDTH,
            font=("Trebuchet MS", 13),
            fg_color=BG_CONTENT,
            border_color=BORDER,
            text_color=TEXT_DARK,
            placeholder_text_color=TEXT_MUTED,
        )
        self._password.pack(padx=PAD_LG, pady=(0, PAD_MD))
        self._password.bind("<Return>", lambda _: self._on_login())

        self._remember = ctk.CTkCheckBox(
            inner,
            text="Remember me",
            font=("Trebuchet MS", 12),
            text_color=TEXT_LIGHT,
            fg_color=ACCENT_END,
            hover_color=BG_CONTENT,
        )
        self._remember.pack(padx=PAD_LG, pady=(PAD_MD, 0))

        if self._client_path:
            ctk.CTkLabel(
                inner,
                text=f"Client: {pathlib.Path(self._client_path).name}",
                font=("Trebuchet MS", 10),
                text_color=TEXT_MUTED,
            ).pack(padx=PAD_LG, pady=(PAD_MD, 0))

        self._login_btn = ctk.CTkButton(
            inner,
            text="PLAY",
            width=ENTRY_WIDTH,
            height=48,
            font=("Trebuchet MS", 16, "bold"),
            fg_color=ACCENT_END,
            text_color=TEXT_DARK,
            hover_color=ACCENT_START,
            border_color=BORDER,
            border_width=2,
            command=self._on_login,
        )
        self._login_btn.pack(padx=PAD_LG, pady=(PAD_LG, PAD_SM))

        self._status = ctk.CTkLabel(
            inner,
            text="",
            font=("Trebuchet MS", 11),
            text_color=TEXT_MUTED,
        )
        self._status.pack(padx=PAD_LG, pady=(PAD_SM, 0))

    def _show_config_panel(self) -> None:
        """Show the settings panel with game executable selection."""
        for child in self._main_container.winfo_children():
            child.destroy()

        panel = ctk.CTkFrame(
            self._main_container,
            fg_color=BG_SURFACE,
            corner_radius=8,
            border_color=BORDER,
            border_width=2,
        )
        panel.pack(fill="both", expand=True, padx=PAD_LG, pady=PAD_LG)

        ctk.CTkButton(
            panel,
            text="← Back",
            width=80,
            height=36,
            fg_color="transparent",
            text_color=TEXT_LIGHT,
            hover_color=BG_CONTENT,
            border_width=0,
            font=("Trebuchet MS", 12),
            command=self._toggle_config,
        ).pack(anchor="w", padx=PAD_MD, pady=PAD_MD)

        ctk.CTkLabel(
            panel,
            text="Settings",
            font=("Trebuchet MS", 20, "bold"),
            text_color=TEXT_LIGHT,
        ).pack(anchor="w", padx=PAD_LG, pady=(0, PAD_SM))

        ctk.CTkLabel(
            panel,
            text="Game executable",
            font=("Trebuchet MS", 12),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=PAD_LG, pady=(PAD_MD, 4))

        path_row = ctk.CTkFrame(panel, fg_color="transparent")
        path_row.pack(anchor="w", padx=PAD_LG, pady=(0, PAD_MD))

        self._client_path_var = ctk.CTkEntry(
            path_row,
            placeholder_text="Select game executable...",
            width=240,
            font=("Trebuchet MS", 12),
            fg_color=BG_CONTENT,
            border_color=BORDER,
            text_color=TEXT_DARK,
            placeholder_text_color=TEXT_MUTED,
        )
        self._client_path_var.pack(side="left", fill="x", expand=True)
        if self._client_path:
            self._client_path_var.insert(0, self._client_path)

        ctk.CTkButton(
            path_row,
            text="Browse",
            width=80,
            height=36,
            font=("Trebuchet MS", 11),
            fg_color=BG_CONTENT,
            text_color=TEXT_DARK,
            hover_color=ACCENT_START,
            border_color=BORDER,
            border_width=1,
            command=self._browse_client,
        ).pack(side="left", padx=PAD_SM)

        ctk.CTkLabel(
            panel,
            text="v0.1.0",
            font=("Trebuchet MS", 10),
            text_color=TEXT_MUTED,
        ).pack(side="bottom", anchor="e", padx=PAD_LG, pady=(0, PAD_MD))

    def _toggle_config(self) -> None:
        """Toggle between login and settings panels."""
        self._show_config = not self._show_config
        if self._show_config:
            self._show_config_panel()
        else:
            self._show_login_panel()

    def _load_saved(self) -> None:
        """Load saved username if remember me was checked."""
        try:
            p = Path("config/remember.txt")
            if p.exists() and (acc := p.read_text().strip()):
                self._account.insert(0, acc)
                self._remember.select()
        except Exception:
            pass

    def _save(self) -> None:
        """Save or remove username based on remember me checkbox."""
        if self._remember.get() and self.account:
            Path("config").mkdir(exist_ok=True)
            Path("config/remember.txt").write_text(self.account)
        else:
            with contextlib.suppress(FileNotFoundError):
                Path("config/remember.txt").unlink()

    def _load_client_path(self) -> None:
        """Load saved client path from config."""
        self._client_path = config.get("client_path", "") or ""

    def _browse_client(self) -> None:
        """Open file dialog to select game executable."""
        path = filedialog.askopenfilename(
            title="Select game executable",
            filetypes=[("Executable", "*"), ("All files", "*")],
        )
        if path:
            self._client_path = path
            self._client_path_var.delete(0, "end")
            self._client_path_var.insert(0, path)
            config.put("client_path", path)

    def _on_login(self) -> None:
        """Handle login button click."""
        path = self._client_path or config.get("client_path", "")
        if not path or not pathlib.Path(path).exists():
            self._status.configure(text="Select game executable in Settings", text_color=ERROR)
            return

        acc = self._account.get().strip()
        pwd = self._password.get()

        if not acc or not pwd:
            self._status.configure(text="Enter account and password", text_color=ERROR)
            return

        self._status.configure(text="Connecting...", text_color=TEXT_MUTED)
        self._login_btn.configure(state="disabled")

        try:
            resp: AuthResponse = api_login(acc, pwd)
            if resp.error:
                self._status.configure(text=resp.error, text_color=ERROR)
            else:
                self.token = resp.token
                self.account = resp.account_id or acc
                self._status.configure(text=f"Welcome, {self.account}", text_color=ACCENT_END)
                self._save()
                self._launch_game(path)
        except Exception as e:
            self._status.configure(text=str(e), text_color=ERROR)
        finally:
            self._login_btn.configure(state="normal")

    def _launch_game(self, path: str) -> None:
        """Launch the game client with the zaap token."""
        if self.token and path:
            try:
                self._zaap.set_token(self.account, self.token)
                client_launcher.launch_game(path, zaap_port=self._zaap.port)
                self._status.configure(text=f"Playing as {self.account}", text_color=ACCENT_END)
            except FileNotFoundError as e:
                messagebox.showerror("Error", f"Game not found: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start: {e}")

    def run(self) -> None:
        """Start the UI main loop."""
        self.mainloop()


def main() -> None:
    """Entry point for the launcher UI."""
    LoginWindow().run()


if __name__ == "__main__":
    main()
