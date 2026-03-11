from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, QUrl
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from logo_engine import (
    GenerationSummary,
    PRACTICAL_FOLDER_GROUPS,
    PracticalPair,
    is_valid_hex_color,
    normalize_hex_color,
    sanitize_name,
)
from v2_app.settings_service import SettingsService
from v2_app.theme import APP_STYLESHEET, APP_TITLE, BRAND_NAME, BRAND_TAGLINE, COLOR_PRIMARY, DEFAULT_CUSTOM_HEX, load_app_icon, load_brand_pixmap
from v2_app.worker import GenerationWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings_service = SettingsService()
        self.scope_buttons: dict[PracticalPair, QToolButton] = {}
        self.worker: GenerationWorker | None = None
        self._brand_pixmap = load_brand_pixmap(34, 34)

        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(load_app_icon())
        self.setAcceptDrops(True)
        self.resize(1220, 860)
        self.setMinimumSize(980, 680)
        self.setStyleSheet(APP_STYLESHEET)

        self._build_ui()
        self._build_menu()
        self._restore_settings()
        self._refresh_preview_path()
        self._refresh_scope_summary()
        self._update_generate_button_state()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(24, 24, 24, 20)
        root_layout.setSpacing(16)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        scroll_host = QWidget()
        scroll_layout = QVBoxLayout(scroll_host)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)

        scroll_layout.addWidget(self._build_header_card())

        body = QWidget()
        body_layout = QGridLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setHorizontalSpacing(16)
        body_layout.setVerticalSpacing(16)
        body_layout.setColumnStretch(0, 3)
        body_layout.setColumnStretch(1, 2)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        left_layout.addWidget(self._build_input_card())
        left_layout.addWidget(self._build_scope_card())
        left_layout.addStretch(1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)
        right_layout.addWidget(self._build_result_card())
        right_layout.addWidget(self._build_log_card(), 1)

        body_layout.addWidget(left, 0, 0)
        body_layout.addWidget(right, 0, 1)

        scroll_layout.addWidget(body)
        scroll_area.setWidget(scroll_host)
        root_layout.addWidget(scroll_area, 1)
        root_layout.addWidget(self._build_footer_bar())

        self.setCentralWidget(root)

    def _build_menu(self) -> None:
        open_action = QAction("저장 폴더 열기", self)
        open_action.triggered.connect(self._open_output_folder)
        self.menuBar().addAction(open_action)

    def _build_header_card(self) -> QFrame:
        card, layout = self._create_card()

        brand_row = QHBoxLayout()
        brand_row.setSpacing(14)

        badge = QFrame()
        badge.setObjectName("softCard")
        badge_layout = QVBoxLayout(badge)
        badge_layout.setContentsMargins(10, 10, 10, 10)
        if self._brand_pixmap:
            image = QLabel()
            image.setPixmap(self._brand_pixmap)
            image.setAlignment(Qt.AlignCenter)
            badge_layout.addWidget(image)
        else:
            fallback = QLabel("LP")
            fallback.setAlignment(Qt.AlignCenter)
            fallback.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: 700;")
            badge_layout.addWidget(fallback)
        brand_row.addWidget(badge, 0, Qt.AlignTop)

        brand_text = QVBoxLayout()
        eyebrow = QLabel(BRAND_NAME)
        eyebrow.setObjectName("eyebrow")
        title = QLabel(APP_TITLE)
        title.setObjectName("title")
        subtitle = QLabel(BRAND_TAGLINE)
        subtitle.setObjectName("muted")
        brand_text.addWidget(eyebrow)
        brand_text.addWidget(title)
        brand_text.addWidget(subtitle)
        brand_row.addLayout(brand_text, 1)

        layout.addLayout(brand_row)

        pill_row = QHBoxLayout()
        pill_row.setSpacing(8)
        pill_row.addWidget(self._build_info_pill("앱 전체 드래그앤드롭"))
        pill_row.addWidget(self._build_info_pill("비동기 자동 생성"))
        pill_row.addWidget(self._build_info_pill("용도별 PNG 정리"))
        pill_row.addStretch(1)
        layout.addLayout(pill_row)
        return card

    def _build_input_card(self) -> QFrame:
        card, layout = self._create_card("입력 설정")

        drop_zone = QFrame()
        drop_zone.setObjectName("dropZone")
        drop_layout = QVBoxLayout(drop_zone)
        drop_layout.setContentsMargins(18, 18, 18, 18)
        drop_layout.setSpacing(6)
        drop_title = QLabel("PNG를 여기로 끌어다 놓아도 바로 첨부됩니다.")
        drop_title.setStyleSheet("font-weight: 700;")
        drop_hint = QLabel("파일 선택 버튼 없이도 창 전체에서 원본 PNG 드래그앤드롭을 지원합니다.")
        drop_hint.setObjectName("muted")
        drop_hint.setWordWrap(True)
        drop_layout.addWidget(drop_title)
        drop_layout.addWidget(drop_hint)
        layout.addWidget(drop_zone)

        self.source_edit = self._add_path_field(
            layout,
            "원본 PNG",
            "파일 선택",
            self._choose_source_png,
            "로고 PNG 1개를 선택하거나 창 어디든 드래그해서 놓을 수 있습니다.",
        )
        self.output_edit = self._add_path_field(
            layout,
            "출력 폴더",
            "폴더 선택",
            self._choose_output_folder,
            "선택한 폴더 안에 브랜드명 기준 결과 폴더가 생성됩니다.",
        )
        self.base_name_edit = self._add_text_field(
            layout,
            "저장 기준 이름",
            "브랜드 폴더명과 파일명 접두사로 함께 사용됩니다.",
        )
        self.hex_edit = self._add_text_field(
            layout,
            "사용자 지정 HEX",
            "예: #1B4797. 색상변형의 custom PNG에 반영됩니다.",
            DEFAULT_CUSTOM_HEX,
        )

        for edit in (self.source_edit, self.output_edit, self.base_name_edit, self.hex_edit):
            edit.textChanged.connect(self._refresh_preview_path)
            edit.textChanged.connect(self._update_generate_button_state)

        return card

    def _build_scope_card(self) -> QFrame:
        card, layout = self._create_card("생성 범위")

        self.scope_summary_label = QLabel()
        self.scope_summary_label.setObjectName("muted")
        layout.addWidget(self.scope_summary_label)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)
        quick_row.addWidget(self._build_action_button("전체 선택", self._select_all_scopes, secondary=True))
        quick_row.addWidget(self._build_action_button("전체 해제", self._clear_all_scopes, secondary=True))
        quick_row.addWidget(self._build_action_button("기본 추천", self._select_recommended_scopes, secondary=True))
        quick_row.addStretch(1)
        layout.addLayout(quick_row)

        for top_folder, subfolders in PRACTICAL_FOLDER_GROUPS.items():
            group_label = QLabel(top_folder)
            group_label.setObjectName("muted")
            group_label.setStyleSheet("font-weight: 700;")
            layout.addWidget(group_label)

            chip_row = QHBoxLayout()
            chip_row.setSpacing(8)
            chip_row.setContentsMargins(0, 0, 0, 8)

            for subfolder in subfolders:
                pair = (top_folder, subfolder)
                chip = QToolButton()
                chip.setText(subfolder)
                chip.setCheckable(True)
                chip.setChecked(True)
                chip.toggled.connect(self._refresh_scope_summary)
                chip_row.addWidget(chip)
                self.scope_buttons[pair] = chip

            chip_row.addStretch(1)
            layout.addLayout(chip_row)

        self.mockup_button = QToolButton()
        self.mockup_button.setText("06_목업 생성")
        self.mockup_button.setCheckable(True)
        self.mockup_button.setChecked(True)
        self.mockup_button.toggled.connect(self._refresh_scope_summary)
        layout.addWidget(self.mockup_button)

        return card

    def _build_result_card(self) -> QFrame:
        card, layout = self._create_card("결과 요약")

        label = QLabel("최종 저장 위치")
        label.setObjectName("muted")
        layout.addWidget(label)

        self.preview_path_value = QLineEdit()
        self.preview_path_value.setReadOnly(True)
        layout.addWidget(self.preview_path_value)

        self.result_summary_label = QLabel("아직 생성 전입니다. 입력값을 채우면 여기서 결과 요약을 보여줍니다.")
        self.result_summary_label.setWordWrap(True)
        self.result_summary_label.setObjectName("muted")
        layout.addWidget(self.result_summary_label)

        self.status_label = QLabel("원본 PNG와 출력 폴더를 선택하면 바로 생성할 수 있습니다.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.progress_note_label = QLabel("생성 전 상태입니다.")
        self.progress_note_label.setObjectName("muted")
        self.progress_note_label.setWordWrap(True)
        layout.addWidget(self.progress_note_label)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.open_folder_button = self._build_action_button("저장 폴더 열기", self._open_output_folder, secondary=True)
        self.generate_button = self._build_action_button("PNG 자동 생성", self._start_generation)
        row.addWidget(self.open_folder_button)
        row.addWidget(self.generate_button)
        layout.addLayout(row)
        return card

    def _build_log_card(self) -> QFrame:
        card, layout = self._create_card("실행 로그")
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addWidget(self._build_action_button("로그 비우기", self._clear_log, secondary=True))
        toolbar.addStretch(1)
        layout.addLayout(toolbar)
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(280)
        layout.addWidget(self.log_text)
        return card

    def _build_footer_bar(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        self.footer_scope_label = QLabel()
        self.footer_scope_label.setObjectName("muted")
        layout.addWidget(self.footer_scope_label, 1)

        self.footer_count_label = QLabel("최근 생성 파일 수 0")
        self.footer_count_label.setObjectName("muted")
        layout.addWidget(self.footer_count_label)
        return card

    def _create_card(self, title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        if title:
            title_label = QLabel(title)
            title_label.setObjectName("sectionTitle")
            layout.addWidget(title_label)

        return card, layout

    def _add_path_field(
        self,
        parent_layout: QVBoxLayout,
        title: str,
        button_text: str,
        callback,
        helper: str,
    ) -> QLineEdit:
        field_wrap = QWidget()
        field_layout = QVBoxLayout(field_wrap)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 700;")
        field_layout.addWidget(title_label)

        row = QHBoxLayout()
        row.setSpacing(8)
        edit = QLineEdit()
        row.addWidget(edit, 1)
        row.addWidget(self._build_action_button(button_text, callback, secondary=True))
        field_layout.addLayout(row)

        helper_label = QLabel(helper)
        helper_label.setObjectName("muted")
        helper_label.setWordWrap(True)
        field_layout.addWidget(helper_label)

        parent_layout.addWidget(field_wrap)
        return edit

    def _add_text_field(
        self,
        parent_layout: QVBoxLayout,
        title: str,
        helper: str,
        value: str = "",
    ) -> QLineEdit:
        field_wrap = QWidget()
        field_layout = QVBoxLayout(field_wrap)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 700;")
        field_layout.addWidget(title_label)

        edit = QLineEdit()
        edit.setText(value)
        field_layout.addWidget(edit)

        helper_label = QLabel(helper)
        helper_label.setObjectName("muted")
        helper_label.setWordWrap(True)
        field_layout.addWidget(helper_label)

        parent_layout.addWidget(field_wrap)
        return edit

    def _build_action_button(self, text: str, callback, secondary: bool = False) -> QPushButton:
        button = QPushButton(text)
        if secondary:
            button.setProperty("role", "secondary")
            button.style().unpolish(button)
            button.style().polish(button)
        button.clicked.connect(callback)
        return button

    def _build_info_pill(self, text: str) -> QFrame:
        pill = QFrame()
        pill.setObjectName("softCard")
        layout = QHBoxLayout(pill)
        layout.setContentsMargins(10, 8, 10, 8)
        label = QLabel(text)
        label.setObjectName("heroTag")
        layout.addWidget(label)
        return pill

    def _restore_settings(self) -> None:
        self.source_edit.setText(self.settings_service.load_string("source_png"))
        self.output_edit.setText(self.settings_service.load_string("output_root"))
        self.base_name_edit.setText(self.settings_service.load_string("base_name"))
        self.hex_edit.setText(self.settings_service.load_string("custom_hex", DEFAULT_CUSTOM_HEX))

        saved_scopes = self.settings_service.load_scope_keys()
        if saved_scopes:
            for pair, button in self.scope_buttons.items():
                button.setChecked(self._pair_to_key(pair) in saved_scopes)
        self.mockup_button.setChecked(self.settings_service.load_mockups_enabled(True))

    def _save_settings(self) -> None:
        self.settings_service.save_string("source_png", self.source_edit.text().strip())
        self.settings_service.save_string("output_root", self.output_edit.text().strip())
        self.settings_service.save_string("base_name", self.base_name_edit.text().strip())
        self.settings_service.save_string("custom_hex", self.hex_edit.text().strip())
        self.settings_service.save_scope_keys(self._selected_scope_keys())
        self.settings_service.save_mockups_enabled(self.mockup_button.isChecked())

    def _refresh_preview_path(self) -> None:
        output_dir = self.output_edit.text().strip()
        source_path = self.source_edit.text().strip()
        base_name = self.base_name_edit.text().strip()

        if not base_name and source_path:
            base_name = Path(source_path).stem

        safe_name = sanitize_name(base_name or "brandlogo")
        preview = str(Path(output_dir) / safe_name) if output_dir else "선택한 출력 폴더 안에 브랜드 폴더가 생성됩니다."
        self.preview_path_value.setText(preview)
        self.open_folder_button.setEnabled(bool(output_dir))
        self._save_settings()

    def _refresh_scope_summary(self) -> None:
        selected_count = len(self._selected_pairs())
        parts = ["원본 보관"]
        if selected_count:
            parts.append(f"실사용 {selected_count}개")
        if self.mockup_button.isChecked():
            parts.append("목업")
        summary = " + ".join(parts)
        self.scope_summary_label.setText(summary)
        self.footer_scope_label.setText(summary)
        self._save_settings()

    def _update_generate_button_state(self) -> None:
        has_source = bool(self.source_edit.text().strip())
        has_output = bool(self.output_edit.text().strip())
        valid_hex = is_valid_hex_color(self.hex_edit.text().strip() or DEFAULT_CUSTOM_HEX)
        self.generate_button.setEnabled(has_source and has_output and valid_hex and self.worker is None)

    def _choose_source_png(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "원본 PNG 선택", "", "PNG Files (*.png)")
        if path:
            self._apply_source_path(Path(path))

    def _choose_output_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if path:
            self.output_edit.setText(path)

    def _apply_source_path(self, path: Path) -> None:
        if path.suffix.lower() != ".png":
            QMessageBox.warning(self, "파일 형식 오류", "PNG 파일만 선택할 수 있습니다.")
            return
        self.source_edit.setText(str(path))
        if not self.base_name_edit.text().strip():
            self.base_name_edit.setText(sanitize_name(path.stem))
        self._append_log(f"원본 PNG 첨부: {path}")

    def _selected_pairs(self) -> set[PracticalPair]:
        return {pair for pair, button in self.scope_buttons.items() if button.isChecked()}

    def _selected_scope_keys(self) -> set[str]:
        return {self._pair_to_key(pair) for pair in self._selected_pairs()}

    @staticmethod
    def _pair_to_key(pair: PracticalPair) -> str:
        return f"{pair[0]}|{pair[1]}"

    def _select_all_scopes(self) -> None:
        for button in self.scope_buttons.values():
            button.setChecked(True)
        self.mockup_button.setChecked(True)

    def _clear_all_scopes(self) -> None:
        for button in self.scope_buttons.values():
            button.setChecked(False)
        self.mockup_button.setChecked(False)

    def _select_recommended_scopes(self) -> None:
        for button in self.scope_buttons.values():
            button.setChecked(True)
        self.mockup_button.setChecked(False)

    def _validate_form(self) -> tuple[Path, Path, str, str]:
        source_path = Path(self.source_edit.text().strip())
        if not source_path.exists() or source_path.suffix.lower() != ".png":
            raise ValueError("원본 PNG 파일을 먼저 선택해 주세요.")

        output_root = Path(self.output_edit.text().strip())
        if not output_root.exists():
            raise ValueError("출력 폴더를 먼저 선택해 주세요.")

        custom_hex = self.hex_edit.text().strip()
        if not is_valid_hex_color(custom_hex):
            raise ValueError("HEX 색상 형식이 올바르지 않습니다. 예: #1B4797")

        base_name = self.base_name_edit.text().strip() or source_path.stem
        return source_path, output_root, base_name, normalize_hex_color(custom_hex)

    def _start_generation(self) -> None:
        try:
            source_path, output_root, base_name, custom_hex = self._validate_form()
        except Exception as exc:
            QMessageBox.warning(self, "입력 오류", str(exc))
            self.status_label.setText(str(exc))
            return

        self.log_text.clear()
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("자동 생성을 시작합니다...")
        self.progress_note_label.setText("이미지 처리와 파일 저장을 진행하는 중입니다.")
        self.generate_button.setEnabled(False)
        self._set_ui_busy(True)
        self._save_settings()

        self.worker = GenerationWorker(
            source_png=source_path,
            output_root=output_root,
            base_name=base_name,
            custom_hex=custom_hex,
            practical_selection=self._selected_pairs(),
            include_mockups=self.mockup_button.isChecked(),
        )
        self.worker.progress.connect(self._append_log)
        self.worker.succeeded.connect(self._handle_generation_success)
        self.worker.failed.connect(self._handle_generation_failure)
        self.worker.finished.connect(self._handle_worker_finished)
        self.worker.start()

    def _handle_generation_success(self, summary: object) -> None:
        if not isinstance(summary, GenerationSummary):
            return

        self.preview_path_value.setText(str(summary.brand_root))
        self.result_summary_label.setText(
            f"총 {summary.saved_count}개 파일을 생성했고, 실사용 폴더 {len(summary.practical_targets)}개를 정리했습니다."
        )
        self.status_label.setText("자동 생성이 완료되었습니다.")
        self.progress_note_label.setText("생성이 끝났습니다. 저장 폴더를 바로 열어 결과를 확인할 수 있습니다.")
        self.footer_count_label.setText(f"최근 생성 파일 수 {summary.saved_count}")
        self._append_log(f"생성 완료: {summary.brand_root}")

    def _handle_generation_failure(self, message: str, traceback_text: str) -> None:
        self.status_label.setText("자동 생성 중 오류가 발생했습니다.")
        self.result_summary_label.setText(message)
        self.progress_note_label.setText("실행 로그를 확인한 뒤 입력값을 조정해 다시 생성해 주세요.")
        self._append_log(traceback_text)
        QMessageBox.critical(self, "생성 오류", message)

    def _handle_worker_finished(self) -> None:
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.worker = None
        self._set_ui_busy(False)
        self._update_generate_button_state()

    def _append_log(self, message: str) -> None:
        self.log_text.appendPlainText(message)

    def _clear_log(self) -> None:
        self.log_text.clear()

    def _set_ui_busy(self, busy: bool) -> None:
        for widget in (
            self.source_edit,
            self.output_edit,
            self.base_name_edit,
            self.hex_edit,
            self.open_folder_button,
        ):
            widget.setEnabled(not busy)

    def _open_output_folder(self) -> None:
        path_text = self.preview_path_value.text().strip()
        if not path_text:
            return
        path = Path(path_text)
        if not path.exists():
            path = Path(self.output_edit.text().strip())
        if path.exists():
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                from PySide6.QtGui import QDesktopServices

                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._save_settings()
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(2000)
        super().closeEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore[override]
        if self._mime_has_png(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore[override]
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return
        local_path = Path(urls[0].toLocalFile())
        self._apply_source_path(local_path)
        event.acceptProposedAction()

    @staticmethod
    def _mime_has_png(mime_data: QMimeData) -> bool:
        return any(url.isLocalFile() and url.toLocalFile().lower().endswith(".png") for url in mime_data.urls())


def create_window() -> MainWindow:
    return MainWindow()
