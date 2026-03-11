from __future__ import annotations

import ctypes
import os
import runpy
import sys
import traceback
from pathlib import Path


PROJECT_DIR = Path(r"C:\Users\cvc90\Desktop\image Converter")
MAIN_FILE = PROJECT_DIR / "main.py"


def show_error(message: str) -> None:
    """파이썬 콘솔 없이도 오류 내용을 볼 수 있게 윈도우 메시지 박스로 보여준다."""
    ctypes.windll.user32.MessageBoxW(0, message, "PNG 로고 자동 생성기 최신실행", 0x10)


def main() -> None:
    try:
        if not PROJECT_DIR.exists():
            raise FileNotFoundError(f"프로젝트 폴더를 찾을 수 없습니다.\n{PROJECT_DIR}")
        if not MAIN_FILE.exists():
            raise FileNotFoundError(f"main.py 파일을 찾을 수 없습니다.\n{MAIN_FILE}")

        os.chdir(PROJECT_DIR)
        sys.path.insert(0, str(PROJECT_DIR))
        runpy.run_path(str(MAIN_FILE), run_name="__main__")
    except Exception:
        show_error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
