from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from v2_app.main_window import create_window
from v2_app.theme import APP_STYLESHEET, load_app_icon


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    app.setWindowIcon(load_app_icon())

    window = create_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
