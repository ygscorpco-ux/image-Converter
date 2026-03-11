from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image, ImageTk, UnidentifiedImageError
except ImportError as exc:  # pragma: no cover - startup guard
    print("Pillow가 설치되어 있지 않습니다. 먼저 'pip install pillow'를 실행해주세요.")
    print(exc)
    raise SystemExit(1)

from logo_engine import PRACTICAL_FOLDER_GROUPS


APP_TITLE = "PNG 로고 파생본 자동 생성기"
DEFAULT_CUSTOM_HEX = "#1B4797"
BRAND_NAME = "LOGOPLANET"
BRAND_TAGLINE = "Professional Brand Identity"
WINDOWS_APP_ID = "LOGOPLANET.PNGAssetStudio"

COLOR_BG = "#F6F8FC"
COLOR_CARD = "#FFFFFF"
COLOR_CARD_SOFT = "#F9FBFF"
COLOR_BORDER = "#DCE5F1"
COLOR_TEXT = "#142033"
COLOR_MUTED = "#66758A"
COLOR_PRIMARY = "#1B4797"
COLOR_PRIMARY_DARK = "#153B79"
COLOR_PRIMARY_SOFT = "#EAF1FB"
COLOR_SUCCESS_SOFT = "#EDF9F5"


def resource_path(relative_path: str) -> Path:
    """개발 실행과 PyInstaller exe 실행 모두에서 공통으로 쓸 리소스 경로를 만든다."""
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / relative_path  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / relative_path


def apply_window_icon(root: tk.Tk) -> None:
    """스크립트 실행과 exe 실행 모두에서 앱 아이콘을 적용한다."""
    png_icon = resource_path("assets/app_icon.png")
    ico_icon = resource_path("assets/app_icon.ico")

    if sys.platform.startswith("win"):
        _apply_windows_app_id()

    if png_icon.exists():
        try:
            icon_image = tk.PhotoImage(file=str(png_icon))
            root.iconphoto(True, icon_image)
            root._icon_image = icon_image  # type: ignore[attr-defined]
        except tk.TclError:
            pass

    if ico_icon.exists():
        try:
            root.iconbitmap(str(ico_icon))
        except tk.TclError:
            pass

        if sys.platform.startswith("win"):
            # Window mapping timing에 따라 기본 Tk 아이콘이 잠깐 보일 수 있어서 몇 번 더 덮어쓴다.
            root.after(0, lambda: _apply_windows_taskbar_icon(root, ico_icon))
            root.after(120, lambda: _apply_windows_taskbar_icon(root, ico_icon))
            root.after(420, lambda: _apply_windows_taskbar_icon(root, ico_icon))


def _apply_windows_app_id() -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except Exception:
        pass


def _apply_windows_taskbar_icon(root: tk.Tk, ico_icon: Path) -> None:
    """윈도우 제목줄과 작업표시줄에서 기본 Tk 아이콘 대신 사용자 아이콘을 유지한다."""
    try:
        hwnd = root.winfo_id()
        image_icon = 1
        load_from_file = 0x0010
        default_size = 0x0040
        wm_seticon = 0x0080
        icon_small = 0
        icon_big = 1

        big_icon = ctypes.windll.user32.LoadImageW(
            None,
            str(ico_icon),
            image_icon,
            32,
            32,
            load_from_file | default_size,
        )
        small_icon = ctypes.windll.user32.LoadImageW(
            None,
            str(ico_icon),
            image_icon,
            16,
            16,
            load_from_file | default_size,
        )

        if big_icon:
            ctypes.windll.user32.SendMessageW(hwnd, wm_seticon, icon_big, big_icon)
        if small_icon:
            ctypes.windll.user32.SendMessageW(hwnd, wm_seticon, icon_small, small_icon)
    except Exception:
        pass


def load_photo_asset(relative_path: str, max_size: tuple[int, int]) -> ImageTk.PhotoImage | None:
    """Pillow 이미지를 읽어 Tkinter에서 안전하게 재사용할 수 있는 객체로 바꾼다."""
    asset_path = resource_path(relative_path)
    if not asset_path.exists():
        return None

    try:
        image = Image.open(asset_path).convert("RGBA")
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    except (OSError, UnidentifiedImageError, tk.TclError):
        return None


class LogoConverterUiMixin:
    def _configure_window_bounds(self) -> None:
        """작은 화면에서도 아래가 잘리지 않도록 초기 창 크기를 화면에 맞춘다."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        width = min(1200, max(980, screen_width - 120))
        height = min(880, max(680, screen_height - 120))

        x = max(24, (screen_width - width) // 2)
        y = max(24, (screen_height - height) // 2)

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(920, 620)

    def _configure_theme(self) -> None:
        self.root.option_add("*Font", "{Malgun Gothic} 10")
        self.root.option_add("*Label.Font", "{Malgun Gothic} 10")

    def _load_brand_images(self) -> None:
        self.brand_badge_image = load_photo_asset("assets/logoplanet_mark.png", (34, 34))
        self.brand_header_image = load_photo_asset("assets/logoplanet_mark.png", (170, 170))
        self.brand_soft_image = load_photo_asset("assets/logoplanet_mark_soft.png", (220, 220))

    def _build_ui(self) -> None:
        footer = tk.Frame(
            self.root,
            bg=COLOR_CARD,
            padx=26,
            pady=18,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            bd=0,
        )
        footer.pack(side="bottom", fill="x")
        self._build_footer_bar(footer)

        viewport = tk.Frame(self.root, bg=COLOR_BG)
        viewport.pack(side="top", fill="both", expand=True)

        self.page_canvas = tk.Canvas(
            viewport,
            bg=COLOR_BG,
            bd=0,
            highlightthickness=0,
            relief="flat",
            yscrollincrement=24,
        )
        self.page_canvas.pack(side="left", fill="both", expand=True)

        self.page_scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=self.page_canvas.yview)
        self.page_scrollbar.pack(side="right", fill="y")
        self.page_canvas.configure(yscrollcommand=self.page_scrollbar.set)

        shell = tk.Frame(self.page_canvas, bg=COLOR_BG, padx=32, pady=28)
        self.scroll_shell = shell
        self.page_window_id = self.page_canvas.create_window((0, 0), window=shell, anchor="nw")
        shell.bind("<Configure>", self._sync_page_scrollregion)
        self.page_canvas.bind("<Configure>", self._resize_scroll_window)
        self.root.bind_all("<MouseWheel>", self._on_global_mousewheel, add="+")

        shell.grid_columnconfigure(0, weight=3, uniform="cols")
        shell.grid_columnconfigure(1, weight=2, uniform="cols")
        shell.grid_rowconfigure(2, weight=1)

        header_card = self._create_card(shell, row=0, column=0, columnspan=2, inner_pad=(26, 18))
        self._build_header(header_card)

        left_column = tk.Frame(shell, bg=COLOR_BG)
        left_column.grid(row=1, column=0, sticky="nsew", padx=(0, 14), pady=(18, 0))
        left_column.grid_columnconfigure(0, weight=1)

        right_column = tk.Frame(shell, bg=COLOR_BG)
        right_column.grid(row=1, column=1, sticky="nsew", padx=(14, 0), pady=(18, 0))
        right_column.grid_columnconfigure(0, weight=1)

        input_card = self._create_card(left_column, row=0, column=0, sticky="ew", inner_pad=(28, 28))
        self._build_input_card(input_card)

        status_card = self._create_card(left_column, row=1, column=0, sticky="ew", pady=(16, 0), inner_pad=(28, 24))
        self._build_status_card(status_card)

        output_card = self._create_card(right_column, row=0, column=0, sticky="ew", inner_pad=(28, 28))
        self._build_output_card(output_card)

        guide_card = self._create_card(right_column, row=1, column=0, sticky="ew", pady=(16, 0), inner_pad=(28, 28))
        self._build_guide_card(guide_card)

        action_card = self._create_card(right_column, row=2, column=0, sticky="ew", pady=(16, 0), inner_pad=(28, 28))
        self._build_action_card(action_card)

        log_card = self._create_card(shell, row=2, column=0, columnspan=2, sticky="nsew", pady=(18, 0), inner_pad=(28, 24))
        self._build_log_card(log_card)

    def _sync_page_scrollregion(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if not self.page_canvas:
            return
        self.page_canvas.configure(scrollregion=self.page_canvas.bbox("all"))

    def _resize_scroll_window(self, event: tk.Event[tk.Misc]) -> None:
        if not self.page_canvas or self.page_window_id is None:
            return
        canvas_width = max(event.width, 760)
        self.page_canvas.itemconfigure(self.page_window_id, width=canvas_width)
        self._sync_page_scrollregion()

    def _on_global_mousewheel(self, event: tk.Event[tk.Misc]) -> str | None:
        if not self.page_canvas:
            return None

        widget = event.widget
        if not isinstance(widget, tk.Misc) or widget.winfo_toplevel() is not self.root:
            return None

        if widget.winfo_class() == "Text":
            return None

        first, last = self.page_canvas.yview()
        if first <= 0.0 and last >= 1.0:
            return None

        delta = getattr(event, "delta", 0)
        if delta == 0:
            return None

        # Windows Tkinter canvas는 작은 wheel repaint가 많을수록 잔상이 더 잘 보여서
        # 한 번에 조금 더 큰 단위로 움직이게 해 redraw 횟수를 줄인다.
        steps = -int(delta / 120) if abs(delta) >= 120 else (-1 if delta > 0 else 1)
        self.page_canvas.yview_scroll(steps * 2, "units")
        return "break"

    def _create_card(
        self,
        parent: tk.Widget,
        row: int,
        column: int,
        *,
        columnspan: int = 1,
        sticky: str = "nsew",
        padx: tuple[int, int] | int = 0,
        pady: tuple[int, int] | int = 0,
        inner_pad: tuple[int, int] = (28, 24),
    ) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=COLOR_CARD,
            bd=0,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_BORDER,
        )
        card.grid(row=row, column=column, columnspan=columnspan, sticky=sticky, padx=padx, pady=pady)
        card.grid_columnconfigure(0, weight=1)

        inner = tk.Frame(card, bg=COLOR_CARD, padx=inner_pad[0], pady=inner_pad[1])
        inner.pack(fill="both", expand=True)
        inner.grid_columnconfigure(0, weight=1)
        return inner

    def _title_label(self, parent: tk.Widget, text: str, *, size: int = 13) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Malgun Gothic", size, "bold"),
        )

    def _text_label(
        self,
        parent: tk.Widget,
        text: str,
        *,
        color: str = COLOR_MUTED,
        wraplength: int | None = None,
        bg: str = COLOR_CARD,
        size: int = 10,
        justify: str = "left",
    ) -> tk.Label:
        label = tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=color,
            font=("Malgun Gothic", size),
            justify=justify,
            anchor="w",
        )
        if wraplength is not None:
            label.configure(wraplength=wraplength)
        return label

    def _variable_label(
        self,
        parent: tk.Widget,
        variable: tk.StringVar,
        *,
        bg: str,
        fg: str,
        font: tuple[str, int] | tuple[str, int, str],
        wraplength: int | None = None,
        justify: str = "left",
    ) -> tk.Label:
        label = tk.Label(
            parent,
            textvariable=variable,
            bg=bg,
            fg=fg,
            font=font,
            justify=justify,
            anchor="w",
        )
        if wraplength is not None:
            label.configure(wraplength=wraplength)
        return label

    def _create_surface_panel(
        self,
        parent: tk.Widget,
        *,
        bg: str = COLOR_CARD_SOFT,
        border: str = COLOR_BORDER,
        padding: tuple[int, int] = (16, 16),
    ) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=bg,
            bd=0,
            highlightthickness=1,
            highlightbackground=border,
            highlightcolor=border,
            padx=padding[0],
            pady=padding[1],
        )

    def _create_field_block(
        self,
        parent: tk.Widget,
        *,
        title: str,
        helper_text: str,
    ) -> tk.Frame:
        block = tk.Frame(parent, bg=COLOR_CARD)
        block.pack(fill="x", pady=(0, 18))
        self._title_label(block, title, size=10).pack(anchor="w")

        content = tk.Frame(block, bg=COLOR_CARD)
        content.pack(fill="x", pady=(8, 6))
        self._text_label(block, helper_text, wraplength=560).pack(anchor="w")
        return content

    def _create_entry_surface(self, parent: tk.Widget) -> tk.Frame:
        return self._create_surface_panel(
            parent,
            bg=COLOR_CARD_SOFT,
            border=COLOR_BORDER,
            padding=(0, 0),
        )

    def _create_entry(self, parent: tk.Widget, variable: tk.StringVar) -> tk.Entry:
        entry = tk.Entry(
            parent,
            textvariable=variable,
            relief="flat",
            bd=0,
            bg=COLOR_CARD_SOFT,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            font=("Malgun Gothic", 11),
        )
        entry.pack(fill="x", ipady=12, padx=14, pady=4)
        return entry

    def _build_guide_item(self, parent: tk.Widget, code: str, title: str, desc: str) -> None:
        row = tk.Frame(parent, bg=COLOR_CARD)
        row.pack(fill="x", pady=6)

        badge = tk.Label(
            row,
            text=code,
            bg=COLOR_PRIMARY_SOFT,
            fg=COLOR_PRIMARY,
            width=4,
            pady=8,
            font=("Malgun Gothic", 9, "bold"),
        )
        badge.pack(side="left")

        text_wrap = tk.Frame(row, bg=COLOR_CARD)
        text_wrap.pack(side="left", fill="x", expand=True, padx=(12, 0))
        self._title_label(text_wrap, title, size=10).pack(anchor="w")
        self._text_label(text_wrap, desc, wraplength=290).pack(anchor="w", pady=(2, 0))

    def _build_header(self, parent: tk.Frame) -> None:
        brand_row = tk.Frame(parent, bg=COLOR_CARD)
        brand_row.pack(fill="x", anchor="w")

        icon_chip = tk.Frame(
            brand_row,
            bg=COLOR_PRIMARY_SOFT,
            highlightthickness=1,
            highlightbackground="#D7E3F8",
            bd=0,
            padx=8,
            pady=8,
        )
        icon_chip.pack(side="left")

        if self.brand_badge_image:
            tk.Label(icon_chip, image=self.brand_badge_image, bg=COLOR_PRIMARY_SOFT).pack()
        else:
            tk.Label(
                icon_chip,
                text="LP",
                bg=COLOR_PRIMARY_SOFT,
                fg=COLOR_PRIMARY,
                font=("Malgun Gothic", 11, "bold"),
            ).pack()

        brand_text_wrap = tk.Frame(brand_row, bg=COLOR_CARD)
        brand_text_wrap.pack(side="left", padx=(14, 0))

        tk.Label(
            brand_text_wrap,
            text=BRAND_NAME,
            bg=COLOR_CARD,
            fg=COLOR_PRIMARY,
            font=("Malgun Gothic", 12, "bold"),
        ).pack(anchor="w")

        tk.Label(
            brand_text_wrap,
            text="PNG BRAND ASSET STUDIO",
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            font=("Malgun Gothic", 9, "bold"),
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            parent,
            text=APP_TITLE,
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Malgun Gothic", 20, "bold"),
        ).pack(anchor="w", pady=(20, 8))

    def _build_brand_panel(self, parent: tk.Frame) -> None:
        panel = tk.Frame(
            parent,
            bg=COLOR_CARD_SOFT,
            bd=0,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            padx=20,
            pady=18,
        )
        panel.pack(fill="x", pady=(0, 8))

        if self.brand_header_image:
            tk.Label(panel, image=self.brand_header_image, bg=COLOR_CARD_SOFT).pack(anchor="center")
        elif self.brand_soft_image:
            tk.Label(panel, image=self.brand_soft_image, bg=COLOR_CARD_SOFT).pack(anchor="center")

        tk.Label(
            panel,
            text=BRAND_NAME,
            bg=COLOR_CARD_SOFT,
            fg=COLOR_TEXT,
            font=("Malgun Gothic", 16, "bold"),
        ).pack(anchor="center", pady=(10, 2))

        tk.Label(
            panel,
            text=BRAND_TAGLINE,
            bg=COLOR_CARD_SOFT,
            fg=COLOR_MUTED,
            font=("Malgun Gothic", 9, "bold"),
        ).pack(anchor="center")

        self._text_label(
            panel,
            "브랜드 기준 로고를 받아 인쇄, 배달앱, 네이버, 인스타그램, 웹사이트용 PNG로 정리하는 작업 흐름을 담았습니다.",
            bg=COLOR_CARD_SOFT,
            wraplength=320,
            justify="center",
        ).pack(anchor="center", pady=(12, 0))

    def _build_stat_block(self, parent: tk.Frame, title: str, value: str) -> None:
        block = self._create_surface_panel(parent, bg=COLOR_CARD_SOFT, border=COLOR_BORDER, padding=(0, 0))
        block.pack(fill="x", pady=6)
        self._text_label(
            block,
            title,
            color=COLOR_MUTED,
            bg=COLOR_CARD_SOFT,
            size=9,
        ).pack(fill="x", padx=14, pady=(8, 0))
        value_label = self._title_label(block, value, size=11)
        value_label.configure(bg=COLOR_CARD_SOFT)
        value_label.pack(fill="x", padx=14, pady=(4, 10), anchor="w")

    def _build_input_card(self, parent: tk.Frame) -> None:
        self._title_label(parent, "입력 설정", size=15).pack(anchor="w")
        self._text_label(
            parent,
            "STEP 1부터 STEP 4까지 순서대로 채우면 됩니다. "
            "창 어디에든 PNG를 드래그해서 놓아도 원본 파일로 바로 첨부됩니다.",
            wraplength=560,
        ).pack(anchor="w", pady=(8, 24))

        self.source_entry = self._create_path_field(
            parent,
            title="STEP 1  원본 PNG",
            variable=self.source_path_var,
            button_text="파일 선택",
            command=self.choose_input_file,
            helper_text="로고 원본 PNG 1개를 선택하세요.",
        )
        self.output_entry = self._create_path_field(
            parent,
            title="STEP 2  출력 폴더",
            variable=self.output_path_var,
            button_text="폴더 선택",
            command=self.choose_output_folder,
            helper_text="이 폴더 안에 브랜드명 기준의 결과 폴더가 생성됩니다.",
        )

        self._create_text_field(
            parent,
            title="STEP 3  저장 기준 이름",
            variable=self.base_name_var,
            helper_text="브랜드 폴더명과 파일명 접두사로 함께 사용됩니다.",
        )
        self._create_text_field(
            parent,
            title="STEP 3-1  사용자 지정 HEX",
            variable=self.custom_hex_var,
            helper_text="예: #1B4797. 사용자 지정 색상 PNG는 이 값을 기준으로 생성됩니다.",
        )
        self._build_scope_selector(parent)

    def _create_path_field(
        self,
        parent: tk.Widget,
        *,
        title: str,
        variable: tk.StringVar,
        button_text: str,
        command: Callable[[], None],
        helper_text: str,
    ) -> tk.Entry:
        control = self._create_field_block(
            parent,
            title=title,
            helper_text=helper_text,
        )
        control.grid_columnconfigure(0, weight=1)
        entry_box = self._create_entry_surface(control)
        entry_box.grid(row=0, column=0, sticky="ew")
        entry = self._create_entry(entry_box, variable)
        self._create_button(control, button_text, command, kind="outline").grid(row=0, column=1, padx=(12, 0))
        return entry

    def _create_text_field(
        self,
        parent: tk.Widget,
        *,
        title: str,
        variable: tk.StringVar,
        helper_text: str,
    ) -> tk.Entry:
        content = self._create_field_block(
            parent,
            title=title,
            helper_text=helper_text,
        )
        entry_box = self._create_entry_surface(content)
        entry_box.pack(fill="x")
        return self._create_entry(entry_box, variable)

    def _build_scope_selector(self, parent: tk.Widget) -> None:
        section = tk.Frame(parent, bg=COLOR_CARD)
        section.pack(fill="x", pady=(6, 0))

        header = tk.Frame(section, bg=COLOR_CARD)
        header.pack(fill="x")
        tk.Label(
            header,
            text="STEP 4  생성 범위",
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Malgun Gothic", 10, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            textvariable=self.scope_summary_var,
            bg=COLOR_CARD,
            fg=COLOR_PRIMARY,
            font=("Malgun Gothic", 9, "bold"),
        ).pack(anchor="w", pady=(6, 0))

        self._text_label(
            section,
            "원본 보관은 항상 생성되고, 아래 용도는 필요한 곳만 골라서 생성할 수 있습니다.",
            wraplength=560,
        ).pack(anchor="w", pady=(8, 14))

        quick_row = tk.Frame(section, bg=COLOR_CARD)
        quick_row.pack(fill="x", pady=(0, 14))
        self._create_button(quick_row, "전체 선택", lambda: self._set_all_scopes(True), kind="soft").pack(side="left")
        self._create_button(quick_row, "전체 해제", lambda: self._set_all_scopes(False), kind="outline").pack(side="left", padx=(10, 0))
        self._create_button(quick_row, "기본 추천", self._set_recommended_scopes, kind="outline").pack(side="left", padx=(10, 0))

        for top_folder, subfolders in PRACTICAL_FOLDER_GROUPS.items():
            group = tk.Frame(section, bg=COLOR_CARD)
            group.pack(fill="x", pady=(0, 12))
            tk.Label(
                group,
                text=top_folder,
                bg=COLOR_CARD,
                fg=COLOR_MUTED,
                font=("Malgun Gothic", 9, "bold"),
            ).pack(anchor="w")

            chip_wrap = tk.Frame(group, bg=COLOR_CARD)
            chip_wrap.pack(fill="x", pady=(8, 0))
            for idx, subfolder in enumerate(subfolders):
                chip = self._create_toggle_chip(
                    chip_wrap,
                    subfolder,
                    self.scope_vars[(top_folder, subfolder)],
                )
                chip.grid(row=idx // 3, column=idx % 3, sticky="w", padx=(0, 10), pady=(0, 10))

        mockup_group = tk.Frame(section, bg=COLOR_CARD)
        mockup_group.pack(fill="x", pady=(0, 6))
        tk.Label(
            mockup_group,
            text="06_목업",
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            font=("Malgun Gothic", 9, "bold"),
        ).pack(anchor="w")
        mockup_chip_wrap = tk.Frame(mockup_group, bg=COLOR_CARD)
        mockup_chip_wrap.pack(fill="x", pady=(8, 0))
        self._create_toggle_chip(mockup_chip_wrap, "목업 생성", self.include_mockups_var).pack(anchor="w")

    def _create_toggle_chip(self, parent: tk.Widget, text: str, variable: tk.BooleanVar) -> tk.Checkbutton:
        chip = tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            onvalue=True,
            offvalue=False,
            indicatoron=False,
            cursor="hand2",
            relief="flat",
            bd=0,
            padx=14,
            pady=9,
            font=("Malgun Gothic", 9, "bold"),
            highlightthickness=1,
            borderwidth=0,
        )
        variable.trace_add("write", lambda *_args, widget=chip, state=variable: self._refresh_toggle_chip(widget, state))
        self._refresh_toggle_chip(chip, variable)
        return chip

    def _refresh_toggle_chip(self, widget: tk.Checkbutton, variable: tk.BooleanVar) -> None:
        if variable.get():
            bg = COLOR_PRIMARY_SOFT
            fg = COLOR_PRIMARY
            border = "#C8D8F3"
        else:
            bg = COLOR_CARD
            fg = COLOR_MUTED
            border = COLOR_BORDER

        widget.configure(
            bg=bg,
            fg=fg,
            activebackground=bg,
            activeforeground=fg,
            selectcolor=bg,
            highlightbackground=border,
            highlightcolor=border,
        )

    def _create_button(
        self,
        parent: tk.Widget,
        text: str,
        command: Callable[[], None],
        *,
        kind: str = "primary",
        fill: bool = False,
    ) -> tk.Button:
        if kind == "primary":
            bg = COLOR_PRIMARY
            hover = COLOR_PRIMARY_DARK
            fg = "#FFFFFF"
            border = COLOR_PRIMARY
        elif kind == "soft":
            bg = COLOR_PRIMARY_SOFT
            hover = "#DCE8FA"
            fg = COLOR_PRIMARY
            border = COLOR_PRIMARY_SOFT
        else:
            bg = COLOR_CARD
            hover = COLOR_PRIMARY_SOFT
            fg = COLOR_PRIMARY
            border = COLOR_BORDER

        button = tk.Button(
            parent,
            text=text,
            command=command,
            cursor="hand2",
            relief="flat",
            bd=0,
            padx=18,
            pady=12,
            bg=bg,
            fg=fg,
            activebackground=hover,
            activeforeground=fg,
            font=("Malgun Gothic", 10, "bold"),
            highlightthickness=1 if kind == "outline" else 0,
            highlightbackground=border,
            highlightcolor=border,
        )
        self._attach_button_hover(button, base_bg=bg, hover_bg=hover, fg=fg)
        if fill:
            button.configure(anchor="center")
        return button

    def _attach_button_hover(self, button: tk.Button, *, base_bg: str, hover_bg: str, fg: str) -> None:
        button.bind("<Enter>", lambda _event: button.configure(bg=hover_bg, fg=fg))
        button.bind("<Leave>", lambda _event: button.configure(bg=base_bg, fg=fg))

    def _build_output_card(self, parent: tk.Frame) -> None:
        self._title_label(parent, "최근 생성 요약", size=15).pack(anchor="w")
        self._text_label(
            parent,
            "현재 저장 기준 경로와 마지막 생성 결과를 한눈에 확인합니다.",
            wraplength=360,
        ).pack(anchor="w", pady=(8, 18))

        path_panel = self._create_surface_panel(parent, bg=COLOR_CARD_SOFT, border=COLOR_BORDER)
        path_panel.pack(fill="x")
        self._variable_label(
            path_panel,
            self.final_path_var,
            bg=COLOR_CARD_SOFT,
            fg=COLOR_TEXT,
            font=("Consolas", 10),
            wraplength=340,
        ).pack(fill="x")

        summary_panel = self._create_surface_panel(parent, bg=COLOR_PRIMARY_SOFT, border="#D8E4F8")
        summary_panel.pack(fill="x", pady=(14, 0))
        self._variable_label(
            summary_panel,
            self.completed_count_var,
            bg=COLOR_PRIMARY_SOFT,
            fg=COLOR_PRIMARY,
            font=("Malgun Gothic", 10, "bold"),
        ).pack(fill="x")
        self._variable_label(
            summary_panel,
            self.scope_summary_var,
            bg=COLOR_PRIMARY_SOFT,
            fg=COLOR_PRIMARY,
            font=("Malgun Gothic", 9, "bold"),
            wraplength=340,
        ).pack(fill="x", pady=(6, 0))
        self._variable_label(
            summary_panel,
            self.result_summary_var,
            bg=COLOR_PRIMARY_SOFT,
            fg=COLOR_TEXT,
            font=("Malgun Gothic", 9),
            wraplength=340,
        ).pack(fill="x", pady=(10, 0))

    def _build_guide_card(self, parent: tk.Frame) -> None:
        self._title_label(parent, "생성 안내", size=15).pack(anchor="w")
        self._text_label(
            parent,
            "미리보기는 빼고, 실제 작업에 필요한 정보만 남겼습니다.",
            wraplength=360,
        ).pack(anchor="w", pady=(8, 18))

        guide_items = [
            ("01", "원본 보관", "원본 / 투명 / 흑백 / 반전 / 색상 기본형을 먼저 저장합니다."),
            ("02", "용도별 생성", "인쇄, 배달앱, 네이버, 인스타그램, 웹사이트 크기로 다시 생성합니다."),
            ("03", "색상 버전 분리", "투명배경 / 흑백 / 반전 / 색상변형 폴더로 나눠 저장합니다."),
        ]

        for code, title, desc in guide_items:
            self._build_guide_item(parent, code, title, desc)

    def _build_action_card(self, parent: tk.Frame) -> None:
        self._title_label(parent, "실행", size=15).pack(anchor="w")
        self._text_label(
            parent,
            "입력값이 준비되면 바로 생성할 수 있습니다. 저장 폴더 열기는 생성 후 결과 확인에 사용합니다.",
            wraplength=360,
        ).pack(anchor="w", pady=(8, 18))

        self._create_button(parent, "PNG 자동 생성", self.run_generation, kind="primary", fill=True).pack(fill="x")
        self._create_button(parent, "저장 폴더 열기", self.open_output_folder, kind="outline", fill=True).pack(fill="x", pady=(12, 0))

    def _build_footer_bar(self, parent: tk.Frame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=0)

        info = tk.Frame(parent, bg=COLOR_CARD)
        info.grid(row=0, column=0, sticky="ew")

        self._text_label(info, "현재 선택 범위", bg=COLOR_CARD, color=COLOR_MUTED, size=9).pack(anchor="w")
        self._variable_label(
            info,
            self.scope_summary_var,
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Malgun Gothic", 11, "bold"),
        ).pack(anchor="w", pady=(4, 2))
        self._variable_label(
            info,
            self.completed_count_var,
            bg=COLOR_CARD,
            fg=COLOR_PRIMARY,
            font=("Malgun Gothic", 9, "bold"),
        ).pack(anchor="w", pady=(0, 2))
        self._variable_label(
            info,
            self.status_var,
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            font=("Malgun Gothic", 9),
            wraplength=560,
        ).pack(anchor="w")

        actions = tk.Frame(parent, bg=COLOR_CARD)
        actions.grid(row=0, column=1, sticky="e", padx=(24, 0))
        self._create_button(actions, "저장 폴더 열기", self.open_output_folder, kind="outline").pack(side="left")
        self._create_button(actions, "PNG 자동 생성", self.run_generation, kind="primary").pack(side="left", padx=(10, 0))

    def _build_status_card(self, parent: tk.Frame) -> None:
        self._title_label(parent, "상태 메시지", size=15).pack(anchor="w")
        self._text_label(
            parent,
            "실행 중 필요한 안내와 오류 메시지가 여기에 표시됩니다.",
            wraplength=560,
        ).pack(anchor="w", pady=(8, 18))

        panel = self._create_surface_panel(parent, bg=COLOR_PRIMARY_SOFT, border=COLOR_PRIMARY_SOFT, padding=(18, 18))
        panel.pack(fill="x")
        self._variable_label(
            panel,
            self.status_var,
            bg=COLOR_PRIMARY_SOFT,
            fg=COLOR_PRIMARY,
            font=("Malgun Gothic", 11, "bold"),
            wraplength=560,
        ).pack(fill="x")

    def _build_log_card(self, parent: tk.Frame) -> None:
        parent.grid_rowconfigure(2, weight=1)
        self._title_label(parent, "실행 로그", size=15).pack(anchor="w")
        self._text_label(
            parent,
            "실제로 어떤 폴더와 파일이 생성되는지 아래에서 확인할 수 있습니다.",
            wraplength=980,
        ).pack(anchor="w", pady=(8, 18))

        log_frame = tk.Frame(
            parent,
            bg=COLOR_CARD_SOFT,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            bd=0,
        )
        log_frame.pack(fill="both", expand=True)
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_frame,
            height=16,
            wrap="word",
            font=("Consolas", 10),
            bg=COLOR_CARD_SOFT,
            fg=COLOR_TEXT,
            bd=0,
            relief="flat",
            padx=16,
            pady=16,
            insertbackground=COLOR_TEXT,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set, state="disabled")
