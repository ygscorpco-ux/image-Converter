from __future__ import annotations

import os
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    DND_FILES = None
    TkinterDnD = None

from app_ui import (
    APP_TITLE,
    COLOR_BG,
    COLOR_PRIMARY,
    COLOR_PRIMARY_SOFT,
    DEFAULT_CUSTOM_HEX,
    LogoConverterUiMixin,
    apply_window_icon,
)
from logo_engine import (
    GenerationRequest,
    GenerationSummary,
    PRACTICAL_FOLDER_GROUPS,
    PracticalPair,
    create_brand_asset_package,
    is_valid_hex_color,
    normalize_hex_color,
    sanitize_name,
)


class LogoConverterApp(LogoConverterUiMixin):
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.configure(bg=COLOR_BG)
        self._configure_window_bounds()

        self.source_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.base_name_var = tk.StringVar()
        self.custom_hex_var = tk.StringVar(value=DEFAULT_CUSTOM_HEX)
        self.scope_summary_var = tk.StringVar()
        self.result_summary_var = tk.StringVar(value="아직 생성 전입니다. 원본과 저장 위치를 정한 뒤 실행하면 결과가 여기에 정리됩니다.")
        self.completed_count_var = tk.StringVar(value="최근 생성 파일 수: 0")
        self.scope_vars: dict[PracticalPair, tk.BooleanVar] = {}
        self.include_mockups_var = tk.BooleanVar(value=True)
        self.final_path_var = tk.StringVar(value="선택한 출력 폴더 안에 브랜드 폴더가 생성됩니다.")
        self.status_var = tk.StringVar(value="원본 PNG와 출력 폴더를 고르면 바로 생성할 수 있습니다.")

        self.base_name_var.trace_add("write", self._on_base_name_changed)
        self.output_path_var.trace_add("write", self._on_output_path_changed)

        self.page_canvas: tk.Canvas | None = None
        self.page_scrollbar: ttk.Scrollbar | None = None
        self.page_window_id: int | None = None
        self.scroll_shell: tk.Frame | None = None
        self.brand_badge_image: ImageTk.PhotoImage | None = None
        self.brand_header_image: ImageTk.PhotoImage | None = None
        self.brand_soft_image: ImageTk.PhotoImage | None = None

        self._configure_theme()
        self._load_brand_images()
        self._init_scope_state()
        self._build_ui()
        self._enable_drag_and_drop()

    def _init_scope_state(self) -> None:
        for top_folder, subfolders in PRACTICAL_FOLDER_GROUPS.items():
            for subfolder in subfolders:
                var = tk.BooleanVar(value=True)
                var.trace_add("write", self._on_scope_changed)
                self.scope_vars[(top_folder, subfolder)] = var

        self.include_mockups_var.trace_add("write", self._on_scope_changed)
        self._update_scope_summary()


    def _enable_drag_and_drop(self) -> None:
        """앱 전체 위젯 어디에 떨어뜨려도 PNG 파일을 받을 수 있게 등록한다."""
        if not DND_FILES or not hasattr(self.root, "drop_target_register"):
            self._append_log("드래그앤드롭은 tkinterdnd2가 있을 때 활성화됩니다.")
            return

        self._register_drop_target(self.root)
        self._append_log("앱 전체 드래그앤드롭이 활성화되었습니다.")

    def _register_drop_target(self, widget: tk.Widget) -> None:
        if hasattr(widget, "drop_target_register") and hasattr(widget, "dnd_bind"):
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._handle_file_drop)
            except tk.TclError:
                pass

        for child in widget.winfo_children():
            self._register_drop_target(child)

    def _handle_file_drop(self, event: object) -> str:
        data = getattr(event, "data", "")
        try:
            dropped_items = self.root.tk.splitlist(data)
        except tk.TclError:
            dropped_items = [str(data)]

        if not dropped_items:
            return "break"

        file_path = Path(dropped_items[0]).expanduser()
        if len(dropped_items) > 1:
            self._append_log("여러 파일이 드롭되어 첫 번째 파일만 사용합니다.")

        try:
            self._apply_selected_png(file_path, source_label="드래그앤드롭")
        except Exception as exc:
            messagebox.showerror("드래그앤드롭 오류", str(exc))
            self._set_status(str(exc))
        return "break"

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.root.update_idletasks()

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)
        self.root.update_idletasks()

    def _build_brand_root_preview(self) -> str:
        output_dir = self.output_path_var.get().strip()
        base_name = sanitize_name(self.base_name_var.get().strip() or Path(self.source_path_var.get() or "brandlogo.png").stem)
        if not output_dir:
            return "선택한 출력 폴더 안에 브랜드 폴더가 생성됩니다."
        return str(Path(output_dir) / base_name)

    def _on_base_name_changed(self, *_args: object) -> None:
        self.final_path_var.set(self._build_brand_root_preview())

    def _on_output_path_changed(self, *_args: object) -> None:
        self.final_path_var.set(self._build_brand_root_preview())

    def _get_selected_practical_pairs(self) -> set[PracticalPair]:
        return {
            key
            for key, var in self.scope_vars.items()
            if var.get()
        }

    def _build_scope_summary_text(self) -> str:
        selected_count = len(self._get_selected_practical_pairs())
        summary_parts = ["원본 보관"]
        if selected_count:
            summary_parts.append(f"실사용 {selected_count}개")
        if self.include_mockups_var.get():
            summary_parts.append("목업")
        return " + ".join(summary_parts)

    def _update_scope_summary(self) -> None:
        self.scope_summary_var.set(self._build_scope_summary_text())

    def _on_scope_changed(self, *_args: object) -> None:
        self._update_scope_summary()

    def _set_all_scopes(self, enabled: bool) -> None:
        for var in self.scope_vars.values():
            var.set(enabled)
        self.include_mockups_var.set(enabled)
        self._update_scope_summary()

    def _set_recommended_scopes(self) -> None:
        for var in self.scope_vars.values():
            var.set(True)
        self.include_mockups_var.set(False)
        self._update_scope_summary()

    def choose_input_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="PNG 파일 선택",
            filetypes=[("PNG files", "*.png")],
        )
        if not file_path:
            return
        try:
            self._apply_selected_png(Path(file_path), source_label="파일 선택")
        except Exception as exc:
            messagebox.showerror("파일 형식 오류", str(exc))
            self._set_status(str(exc))

    def _apply_selected_png(self, file_path: Path, *, source_label: str) -> None:
        if file_path.suffix.lower() != ".png":
            raise ValueError("PNG 파일만 첨부할 수 있습니다.")
        if not file_path.exists():
            raise ValueError("선택한 PNG 파일을 찾을 수 없습니다.")

        self.source_path_var.set(str(file_path))

        if not self.base_name_var.get().strip():
            self.base_name_var.set(sanitize_name(file_path.stem))

        self.final_path_var.set(self._build_brand_root_preview())
        self._append_log(f"{source_label}로 원본 PNG 첨부: {file_path}")
        self._set_status(f"{source_label}로 PNG 첨부 완료. 출력 폴더를 고른 뒤 바로 자동 생성을 실행할 수 있습니다.")

    def choose_output_folder(self) -> None:
        folder_path = filedialog.askdirectory(title="출력 폴더 선택")
        if not folder_path:
            return

        self.output_path_var.set(folder_path)
        self.final_path_var.set(self._build_brand_root_preview())
        self._set_status("출력 폴더 선택 완료. 이 위치 안에 브랜드명 폴더가 생성됩니다.")

    def _validate_form_inputs(self) -> tuple[Path, str]:
        source_text = self.source_path_var.get().strip()
        if not source_text:
            raise ValueError("PNG 파일을 먼저 선택해주세요.")

        source_path = Path(source_text)
        if source_path.suffix.lower() != ".png":
            raise ValueError("PNG 파일만 선택할 수 있습니다.")
        if not source_path.exists():
            raise ValueError("선택한 PNG 파일을 찾을 수 없습니다.")

        custom_hex = self.custom_hex_var.get().strip()
        if not is_valid_hex_color(custom_hex):
            raise ValueError("HEX 색상 형식이 올바르지 않습니다. 예: #1B4797")

        return source_path, normalize_hex_color(custom_hex)

    def _build_generation_request(self) -> GenerationRequest:
        source_path, custom_hex = self._validate_form_inputs()
        output_text = self.output_path_var.get().strip()
        if not output_text:
            raise ValueError("출력 폴더를 선택해주세요.")

        output_root = Path(output_text)
        if not output_root.exists():
            raise ValueError("선택한 출력 폴더를 찾을 수 없습니다.")

        return GenerationRequest(
            source_png=source_path,
            output_root=output_root,
            base_name=self.base_name_var.get().strip() or source_path.stem,
            custom_hex=custom_hex,
            practical_selection=self._get_selected_practical_pairs(),
            include_mockups=self.include_mockups_var.get(),
        )

    def _prepare_generation_run(self) -> None:
        self._clear_log()
        self._update_scope_summary()
        self._set_status("자동 생성 작업을 시작합니다...")
        self.root.config(cursor="watch")

    def _apply_generation_success(self, summary: GenerationSummary) -> None:
        self.final_path_var.set(str(summary.brand_root))
        self.completed_count_var.set(f"최근 생성 파일 수: {summary.saved_count}")
        self.result_summary_var.set(
            f"{self._build_scope_summary_text()} 기준으로 생성했습니다. "
            f"실사용 폴더 {len(summary.practical_targets)}개가 저장 경로 안에 정리됩니다."
        )
        self._set_status(
            f"자동 생성 완료. 총 {summary.saved_count}개 파일을 저장했고, "
            f"{len(summary.practical_targets)}개 실사용 폴더에 정리했습니다."
        )
        self._append_log(f"작업 완료 폴더: {summary.brand_root}")
        messagebox.showinfo(
            "생성 완료",
            (
                "PNG 파생본 생성이 완료되었습니다.\n\n"
                f"저장 위치:\n{summary.brand_root}\n\n"
                f"총 저장 파일 수: {summary.saved_count}"
            ),
        )

    def _handle_generation_failure(self, exc: Exception) -> None:
        traceback_text = traceback.format_exc()
        self._append_log(traceback_text)
        messagebox.showerror("생성 오류", f"파일 생성 중 오류가 발생했습니다.\n\n{exc}")
        self.result_summary_var.set("생성에 실패했습니다. 입력값과 실행 로그를 확인해 주세요.")
        self._set_status("파일 생성 실패. 실행 로그를 확인해주세요.")

    def run_generation(self) -> None:
        try:
            request = self._build_generation_request()
        except Exception as exc:
            messagebox.showerror("입력 오류", str(exc))
            self._set_status(str(exc))
            return

        self._prepare_generation_run()

        try:
            summary = create_brand_asset_package(
                source_png=request.source_png,
                output_root=request.output_root,
                base_name=request.base_name,
                custom_hex=request.custom_hex,
                practical_selection=request.practical_selection,
                include_mockups=request.include_mockups,
                logger=self._append_log,
            )
            self._apply_generation_success(summary)
        except Exception as exc:
            self._handle_generation_failure(exc)
        finally:
            self.root.config(cursor="")

    def open_output_folder(self) -> None:
        target = self.final_path_var.get().strip()
        if not target or target == "선택한 출력 폴더 안에 브랜드 폴더가 생성됩니다.":
            messagebox.showinfo("안내", "먼저 출력 폴더를 선택해주세요.")
            return

        try:
            path = Path(target)
            if not path.exists():
                path = Path(self.output_path_var.get().strip())

            if path.exists():
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                messagebox.showinfo("안내", "열 수 있는 폴더가 아직 없습니다. 먼저 자동 생성을 실행해주세요.")
        except Exception as exc:
            messagebox.showerror("폴더 열기 오류", f"폴더를 열 수 없습니다.\n\n{exc}")


def launch_app() -> None:
    root = TkinterDnD.Tk() if TkinterDnD else tk.Tk()
    apply_window_icon(root)
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Vertical.TScrollbar", troughcolor=COLOR_BG, background=COLOR_PRIMARY_SOFT, bordercolor=COLOR_BG)

    app = LogoConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch_app()
