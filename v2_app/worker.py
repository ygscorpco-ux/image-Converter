from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from logo_engine import GenerationSummary, PracticalPair, create_brand_asset_package


class GenerationWorker(QThread):
    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str, str)

    def __init__(
        self,
        *,
        source_png: Path,
        output_root: Path,
        base_name: str,
        custom_hex: str,
        practical_selection: set[PracticalPair],
        include_mockups: bool,
    ) -> None:
        super().__init__()
        self._source_png = source_png
        self._output_root = output_root
        self._base_name = base_name
        self._custom_hex = custom_hex
        self._practical_selection = practical_selection
        self._include_mockups = include_mockups

    def run(self) -> None:
        try:
            summary: GenerationSummary = create_brand_asset_package(
                source_png=self._source_png,
                output_root=self._output_root,
                base_name=self._base_name,
                custom_hex=self._custom_hex,
                practical_selection=self._practical_selection,
                include_mockups=self._include_mockups,
                logger=self.progress.emit,
            )
            self.succeeded.emit(summary)
        except Exception as exc:
            self.failed.emit(str(exc), traceback.format_exc())

