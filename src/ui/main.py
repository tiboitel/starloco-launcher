"""Launcher UI - Modern minimalist dark theme with gold accent."""

import contextlib
import pathlib
import threading
from pathlib import Path

import customtkinter as ctk
from customtkinter import CTkLabel, CTkEntry, CTkButton, CTkCheckBox, CTkScrollableFrame, CTkFrame

from src.api import login as api_login
from src.api.mock import AuthResponse
from src.client import launcher as client_launcher
from src import config
from src.zaap.server import ZaapAuth
from tkinter import filedialog, messagebox

# Color system
BG_MAIN = "#0a0a0a"
BG_SURFACE = "#141414"
BG_SURFACE_HOVER = "#1e1e1e"
TEXT_MAIN = "#e0e0e0"
TEXT_MUTED = "#6e6e6e"
BORDER = "#2a2a2a"
ACCENT = "#c9a227"
ACCENT_HOVER = "#b8911f"
ACCENT_DISABLED = "#3d3520"
ERROR = "#c42b1c"

# Layout constants
WINDOW_WIDTH = 860
WINDOW_HEIGHT = 520
TOP_BAR_HEIGHT = 36
PAD_SM = 12
PAD_MD = 16
PAD_LG = 24
PAD_XL = 32
ENTRY_WIDTH = 300


class LoginWindow(ctk.CTk):
    """Modern minimalist launcher window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Starloco")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        ctk.set_appearance_mode("dark")

        self.token: str | None = None
        self.account: str | None = None
        self._show_config = False
        self._config_panel = None
        self._login_card_frame = None
        self._news_panel_frame = None
        self._client_path = ""
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._zaap = ZaapAuth()
        self._zaap.start()
        self._zaap_thread = threading.Thread(target=self._zaap.accept_loop, daemon=True)
        self._zaap_thread.start()

        self._build_ui()
        self._load_saved()
        self._load_client_path()
        self.after(100, self._account.focus_set)

    def _build_ui(self) -> None:
        # Top bar (fixed width to cover entire window)
        self._build_top_bar()

        # Main container (swappable)
        self._main_container = ctk.CTkFrame(self, fg_color="transparent")
        self._main_container.pack(fill="both", expand=True, pady=(TOP_BAR_HEIGHT, 0))

        # Default: show login + news
        self._show_login_panel()

    def _show_login_panel(self) -> None:
        # Clear container
        for child in self._main_container.winfo_children():
            child.destroy()

        # Left login card
        self._login_card_frame = ctk.CTkFrame(
            self._main_container,
            fg_color=BG_MAIN,
            width=360,
            corner_radius=12,
            border_color=BORDER,
            border_width=1,
        )
        self._login_card_frame.pack(side="left", fill="both", padx=PAD_LG, pady=PAD_LG)
        self._login_card(self._login_card_frame)

        # Right news column
        self._news_panel_frame = CTkFrame(
            self._main_container, fg_color=BG_SURFACE, corner_radius=12
        )
        self._news_panel_frame.pack(
            side="right", fill="both", expand=True, padx=PAD_LG, pady=PAD_LG
        )
        self._news_panel(self._news_panel_frame)

    def _show_config_panel(self) -> None:
        # Clear container
        for child in self._main_container.winfo_children():
            child.destroy()

        self._config_panel = ctk.CTkFrame(
            self._main_container,
            fg_color=BG_MAIN,
            width=360,
            corner_radius=12,
            border_color=BORDER,
            border_width=1,
        )
        self._config_panel.pack(fill="both", expand=True, padx=PAD_LG, pady=PAD_LG)
        self._config_panel.pack_propagate(False)
        self._build_config_form(self._config_panel)

    def _build_config_form(self, parent: ctk.CTkFrame) -> None:
        CTkLabel(
            parent,
            text="Settings",
            font=("Inter", 11),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=PAD_LG, pady=(PAD_LG, 4))

        CTkLabel(
            parent,
            text="Configuration",
            font=("Inter", 20, "bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=PAD_LG, pady=(0, PAD_LG))

        CTkLabel(
            parent,
            text="Game executable",
            font=("Inter", 11),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=PAD_LG, pady=(PAD_MD, 4))

        # Path display + browse button row
        path_row = ctk.CTkFrame(parent, fg_color="transparent")
        path_row.pack(anchor="w", padx=PAD_LG, pady=(0, PAD_MD))

        self._client_path_var = ctk.CTkEntry(
            path_row,
            placeholder_text="Select game executable...",
            width=220,
            font=("Inter", 11),
            fg_color=BG_SURFACE,
            border_color=BORDER,
            text_color=TEXT_MAIN,
            placeholder_text_color=TEXT_MUTED,
        )
        self._client_path_var.pack(side="left", fill="x", expand=True)
        if self._client_path:
            self._client_path_var.insert(0, self._client_path)

        CTkButton(
            path_row,
            text="Browse",
            width=70,
            height=32,
            font=("Inter", 10),
            fg_color=BG_SURFACE,
            text_color=TEXT_MAIN,
            hover_color=BG_SURFACE_HOVER,
            border_color=BORDER,
            border_width=1,
            command=self._browse_client,
        ).pack(side="left", padx=PAD_SM, pady=0)

        CTkLabel(
            parent,
            text="v0.1.0",
            font=("Inter", 9),
            text_color="#333333",
        ).pack(side="bottom", anchor="e", padx=PAD_LG, pady=(0, PAD_MD))

    def _build_top_bar(self) -> None:
        """Top bar with drag and close button."""
        top = ctk.CTkFrame(
            self,
            fg_color=BG_MAIN,
            width=WINDOW_WIDTH,
            height=TOP_BAR_HEIGHT,
            corner_radius=0,
        )
        top.pack(fill="x")

        # Draggable area (left side)
        drag = CTkFrame(
            top,
            fg_color="transparent",
            cursor="fleur",
            width=WINDOW_WIDTH - 60,
            height=TOP_BAR_HEIGHT,
        )
        drag.pack(side="left", fill="both", padx=(PAD_SM, 0))
        drag.bind("<Button-1>", self._on_drag_start)
        drag.bind("<B1-Motion>", self._on_drag_motion)

        CTkLabel(
            drag,
            text="STARLOCO",
            font=("Inter", 14, "bold"),
            text_color=ACCENT,
        ).pack(side="left", padx=PAD_MD, pady=PAD_SM)

        # Close button (pack first - appears rightmost)
        close = CTkButton(
            top,
            text="✕",
            width=36,
            height=28,
            fg_color="transparent",
            text_color=TEXT_MUTED,
            hover_color=ERROR,
            border_width=0,
            corner_radius=0,
            font=("Inter", 10),
            command=self.quit,
        )
        close.pack(side="right", padx=PAD_SM, pady=4)

        # Minimize button (pack second)
        minimize = CTkButton(
            top,
            text="_",
            width=36,
            height=28,
            fg_color="transparent",
            text_color=TEXT_MUTED,
            hover_color=BG_SURFACE_HOVER,
            border_width=0,
            corner_radius=0,
            font=("Inter", 12),
            command=self.iconify,
        )
        minimize.pack(side="right", padx=PAD_SM, pady=4)

        # Config button (cog icon, pack last - appears leftmost)
        self._config_btn = CTkButton(
            top,
            text="⚙",
            width=40,
            height=28,
            fg_color="transparent",
            text_color=TEXT_MUTED,
            hover_color=BG_SURFACE_HOVER,
            border_width=0,
            corner_radius=0,
            font=("Inter", 12),
            command=self._toggle_config,
        )
        self._config_btn.pack(side="right", padx=(0, PAD_SM), pady=4)

    def _on_drag_start(self, event) -> None:
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag_motion(self, event) -> None:
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        self.geometry(f"+{self.winfo_x() + dx}+{self.winfo_y() + dy}")

    def _toggle_config(self) -> None:
        self._show_config = not self._show_config
        if self._show_config:
            self._show_config_panel()
        else:
            self._show_login_panel()

    def _login_card(self, main) -> None:
        """Left login form as a floating card."""
        card = CTkFrame(
            main,
            fg_color=BG_MAIN,
            width=360,
            corner_radius=12,
            border_color=BORDER,
            border_width=1,
        )
        card.pack(side="left", fill="both", padx=PAD_LG, pady=PAD_LG)
        card.pack_propagate(False)

        ctk.CTkLabel(
            card,
            text="Welcome back",
            font=("Inter", 11),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=PAD_LG, pady=(PAD_LG, 4))

        ctk.CTkLabel(
            card,
            text="Sign in to play",
            font=("Inter", 20, "bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=PAD_LG, pady=(0, PAD_LG))

        # Form fields with proper spacing
        self._account = CTkEntry(
            card,
            placeholder_text="Username",
            width=ENTRY_WIDTH,
            font=("Inter", 12),
            fg_color=BG_SURFACE,
            border_color=BORDER,
            text_color=TEXT_MAIN,
            placeholder_text_color=TEXT_MUTED,
        )
        self._account.pack(anchor="w", padx=PAD_LG, pady=(0, PAD_MD))
        self._account.bind("<Return>", lambda _: self._on_login())

        self._password = CTkEntry(
            card,
            placeholder_text="Password",
            show="*",
            width=ENTRY_WIDTH,
            font=("Inter", 12),
            fg_color=BG_SURFACE,
            border_color=BORDER,
            text_color=TEXT_MAIN,
            placeholder_text_color=TEXT_MUTED,
        )
        self._password.pack(anchor="w", padx=PAD_LG, pady=(0, PAD_MD))
        self._password.bind("<Return>", lambda _: self._on_login())

        # Remember me
        self._remember = CTkCheckBox(
            card,
            text="Remember me",
            font=("Inter", 11),
            text_color=TEXT_MUTED,
            fg_color=ACCENT,
            hover_color=BG_SURFACE_HOVER,
        )
        self._remember.pack(anchor="w", padx=PAD_LG, pady=(PAD_MD, 0))

        # Client path hint
        if self._client_path:
            CTkLabel(
                card,
                text=f"Client: {pathlib.Path(self._client_path).name}",
                font=("Inter", 9),
                text_color=TEXT_MUTED,
            ).pack(anchor="w", padx=PAD_LG, pady=(PAD_MD, 0))

        # Login button
        self._login_btn = CTkButton(
            card,
            text="Sign In",
            width=ENTRY_WIDTH,
            height=40,
            font=("Inter", 12, "bold"),
            fg_color=BG_SURFACE,
            text_color=TEXT_MAIN,
            hover_color=BG_SURFACE_HOVER,
            border_color=BORDER,
            border_width=1,
            command=self._on_login,
        )
        self._login_btn.pack(anchor="w", padx=PAD_LG, pady=(PAD_LG, PAD_SM))

        # Status message
        self._status = CTkLabel(
            card,
            text="",
            font=("Inter", 10),
            text_color=TEXT_MUTED,
        )
        self._status.pack(anchor="w", padx=PAD_LG, pady=(PAD_SM, 0))

        # Spacer
        card.pack(fill="both", expand=True)

    def _news_panel(self, parent: CTkFrame) -> None:
        # Header
        CTkLabel(
            parent,
            text="News",
            font=("Inter", 12, "bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", padx=PAD_LG, pady=(PAD_MD, PAD_SM))

        # Scrollable frame
        scroll = CTkScrollableFrame(
            parent,
            fg_color="transparent",
            scrollbar_button_color=BG_SURFACE_HOVER,
            scrollbar_fg_color=BORDER,
        )
        scroll.pack(fill="both", expand=True, padx=PAD_MD, pady=(0, PAD_MD))

        # News items
        self._news_item(scroll, "Welcome", "Get started with Starloco")
        self._news_item(scroll, "Login", "Sign in to play")
        self._news_item(scroll, "Play", "Launch your game instantly")

        # Version footer
        CTkLabel(
            parent,
            text="v0.1.0",
            font=("Inter", 9),
            text_color="#333333",
        ).pack(side="bottom", anchor="e", padx=PAD_LG, pady=(0, PAD_MD))

    def _news_item(self, parent, title: str, content: str) -> None:
        card = CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=8)
        card.pack(fill="x", pady=(0, PAD_SM))

        CTkLabel(
            card,
            text=title,
            font=("Inter", 11, "bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=PAD_MD, pady=(PAD_SM, 2))

        CTkLabel(
            card,
            text=content,
            font=("Inter", 10),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=PAD_MD, pady=(0, PAD_SM))

    def _load_saved(self) -> None:
        try:
            p = Path("config/remember.txt")
            if p.exists() and (acc := p.read_text().strip()):
                self._account.insert(0, acc)
                self._remember.select()
        except Exception:
            pass

    def _save(self) -> None:
        if self._remember.get() and self.account:
            Path("config").mkdir(exist_ok=True)
            Path("config/remember.txt").write_text(self.account)
        else:
            with contextlib.suppress(FileNotFoundError):
                Path("config/remember.txt").unlink()

    def _load_client_path(self) -> None:
        self._client_path = config.get("client_path", "") or ""

    def _browse_client(self) -> None:
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
        # Validate client path first (fail-fast)
        path = self._client_path or config.get("client_path", "")
        if not path or not pathlib.Path(path).exists():
            self._status.configure(text="Select game executable in Config", text_color=ERROR)
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
                self._status.configure(text=f"Welcome, {self.account}", text_color=ACCENT)
                self._save()
                self._launch_game(path)
        except Exception as e:
            self._status.configure(text=str(e), text_color=ERROR)
        finally:
            self._login_btn.configure(state="normal")

    def _launch_game(self, path: str) -> None:
        if self.token and path:
            try:
                self._zaap.set_token(self.account, self.token)

                client_launcher.launch_game(path, zaap_port=self._zaap.port)

                self._status.configure(text=f"Playing as {self.account}", text_color=ACCENT)
            except FileNotFoundError as e:
                messagebox.showerror("Error", f"Game not found: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start: {e}")

    def run(self) -> None:
        self.mainloop()


def main() -> None:
    LoginWindow().run()


if __name__ == "__main__":
    main()
