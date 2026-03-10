from __future__ import annotations

import ctypes
import os
import re
import shutil
import sys
import traceback
from dataclasses import dataclass
from collections import Counter, deque
from datetime import datetime
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    DND_FILES = None
    TkinterDnD = None

try:
    from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageTk, UnidentifiedImageError
except ImportError as exc:  # pragma: no cover - startup guard
    print("Pillow가 설치되어 있지 않습니다. 먼저 'pip install pillow'를 실행해주세요.")
    print(exc)
    raise SystemExit(1)


APP_TITLE = "PNG 로고 파생본 자동 생성기"
DEFAULT_CUSTOM_HEX = "#1B4797"
BRAND_NAME = "LOGOPLANET"
BRAND_TAGLINE = "Professional Brand Identity"
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'

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

# 기준 보관 폴더와 실사용 폴더 구조를 문서와 동일하게 맞춘다.
ORIGINAL_REFERENCE_FOLDERS = {
    "original": ("00_원본", "원본그대로"),
    "transparent": ("00_원본", "투명배경기본형"),
    "black": ("00_원본", "흑백기본형"),
    "white": ("00_원본", "흑백기본형"),
    "grayscale": ("00_원본", "흑백기본형"),
    "invert": ("00_원본", "반전기본형"),
    "color_red": ("00_원본", "색상변형기본형"),
    "color_blue": ("00_원본", "색상변형기본형"),
    "color_green": ("00_원본", "색상변형기본형"),
    "color_yellow": ("00_원본", "색상변형기본형"),
    "color_custom": ("00_원본", "색상변형기본형"),
}

PRACTICAL_FOLDER_GROUPS = {
    "01_인쇄": ("명함", "메뉴판", "포스터", "스티커", "간판"),
    "02_배달앱": ("배민", "쿠팡이츠", "요기요"),
    "03_네이버": ("플레이스", "블로그", "카페"),
    "04_인스타그램": ("프로필", "피드", "스토리"),
    "05_웹사이트": ("헤더로고", "파비콘", "공유썸네일"),
}

COMMON_VARIANT_FOLDERS = ("투명배경", "흑백", "반전", "색상변형")

PRACTICAL_VARIANT_DESTINATIONS = {
    "transparent": "투명배경",
    "black": "흑백",
    "white": "흑백",
    "grayscale": "흑백",
    "invert": "반전",
    "color_red": "색상변형",
    "color_blue": "색상변형",
    "color_green": "색상변형",
    "color_yellow": "색상변형",
    "color_custom": "색상변형",
}

FIXED_COLOR_VARIANTS = {
    "color_red": (220, 53, 69),
    "color_blue": (27, 71, 151),
    "color_green": (28, 130, 79),
    "color_yellow": (232, 181, 35),
}

VARIANT_DISPLAY_NAMES = {
    "original": "원본 복사본",
    "transparent": "투명 배경",
    "black": "검정",
    "white": "흰색",
    "grayscale": "회색조",
    "invert": "반전",
    "color_red": "빨강",
    "color_blue": "파랑",
    "color_green": "초록",
    "color_yellow": "노랑",
    "color_custom": "사용자 지정 색상",
}

VARIANT_FILENAME_LABELS = {
    "transparent": "",
    "black": "black",
    "white": "white",
    "grayscale": "grayscale",
    "invert": "invert",
    "color_red": "red",
    "color_blue": "blue",
    "color_green": "green",
    "color_yellow": "yellow",
    "color_custom": "custom",
}

VARIANT_GROUP_TO_KEYS = {
    "투명배경": ("transparent",),
    "흑백": ("black", "white", "grayscale"),
    "반전": ("invert",),
    "색상변형": ("color_red", "color_blue", "color_green", "color_yellow", "color_custom"),
}


@dataclass(frozen=True)
class AssetPreset:
    stem: str
    size: tuple[int, int]
    padding: float = 0.12
    background: tuple[int, int, int, int] = (0, 0, 0, 0)


MASTER_CANVAS_PRESETS = (
    AssetPreset("square_master", (3000, 3000), padding=0.14),
    AssetPreset("horizontal_master", (3000, 1800), padding=0.10),
    AssetPreset("vertical_master", (3000, 3750), padding=0.14),
)

PRACTICAL_ASSET_PRESETS: dict[tuple[str, str], tuple[AssetPreset, ...]] = {
    ("01_인쇄", "명함"): (
        AssetPreset("businesscard_logo", (1063, 591), padding=0.10),
    ),
    ("01_인쇄", "메뉴판"): (
        AssetPreset("menu_a4_logo", (2480, 3508), padding=0.10),
    ),
    ("01_인쇄", "포스터"): (
        AssetPreset("poster_a3_logo", (3508, 4961), padding=0.10),
    ),
    ("01_인쇄", "스티커"): (
        AssetPreset("sticker_square_logo", (591, 591), padding=0.12),
    ),
    ("01_인쇄", "간판"): (
        AssetPreset("sign_mock_logo", (4000, 4000), padding=0.16),
    ),
    ("02_배달앱", "배민"): (
        AssetPreset("baemin_logo", (170, 170), padding=0.18),
        AssetPreset("baemin_logo_hd", (1020, 1020), padding=0.16),
        AssetPreset("baemin_store", (1200, 1200), padding=0.14),
        AssetPreset("baemin_menu", (1280, 960), padding=0.12),
    ),
    ("02_배달앱", "쿠팡이츠"): (
        AssetPreset("coupangeats_logo", (1080, 1080), padding=0.16),
        AssetPreset("coupangeats_store", (1080, 1080), padding=0.14),
        AssetPreset("coupangeats_menu", (1080, 660), padding=0.12),
    ),
    ("02_배달앱", "요기요"): (
        AssetPreset("yogiyo_logo", (300, 300), padding=0.18),
        AssetPreset("yogiyo_store", (1080, 1080), padding=0.14),
        AssetPreset("yogiyo_background", (1080, 640), padding=0.12),
        AssetPreset("yogiyo_menu", (1080, 640), padding=0.12),
    ),
    ("03_네이버", "플레이스"): (
        AssetPreset("naver_place_main", (1200, 750), padding=0.12),
        AssetPreset("naver_place_logo", (720, 720), padding=0.16),
        AssetPreset("naver_place_thumb", (720, 720), padding=0.14),
    ),
    ("03_네이버", "블로그"): (
        AssetPreset("naver_blog_title", (966, 300), padding=0.10),
        AssetPreset("naver_blog_profile", (400, 400), padding=0.16),
        AssetPreset("naver_blog_thumb", (1200, 750), padding=0.12),
    ),
    ("03_네이버", "카페"): (
        AssetPreset("naver_cafe_profile", (300, 300), padding=0.18),
        AssetPreset("naver_cafe_banner", (1200, 750), padding=0.12),
        AssetPreset("naver_cafe_thumb", (720, 720), padding=0.14),
    ),
    ("04_인스타그램", "프로필"): (
        AssetPreset("instagram_profile", (1080, 1080), padding=0.20),
    ),
    ("04_인스타그램", "피드"): (
        AssetPreset("instagram_feed_square", (1080, 1080), padding=0.12),
        AssetPreset("instagram_feed_vertical", (1080, 1350), padding=0.12),
    ),
    ("04_인스타그램", "스토리"): (
        AssetPreset("instagram_story", (1080, 1920), padding=0.12),
        AssetPreset("instagram_reels_cover", (420, 654), padding=0.10),
    ),
    ("05_웹사이트", "헤더로고"): (
        AssetPreset("header_logo_light", (1200, 300), padding=0.08),
        AssetPreset("header_logo_dark", (1200, 300), padding=0.08),
    ),
    ("05_웹사이트", "파비콘"): (
        AssetPreset("favicon", (48, 48), padding=0.14),
        AssetPreset("favicon", (96, 96), padding=0.14),
        AssetPreset("favicon", (192, 192), padding=0.14),
        AssetPreset("favicon", (512, 512), padding=0.14),
    ),
    ("05_웹사이트", "공유썸네일"): (
        AssetPreset("share_thumb", (1200, 630), padding=0.12),
        AssetPreset("share_square", (1200, 1200), padding=0.14),
    ),
}

MOCKUP_PRESETS = (
    AssetPreset("mockup_businesscard", (1600, 1000), padding=0.22, background=(247, 247, 247, 255)),
    AssetPreset("mockup_menu", (1600, 2200), padding=0.18, background=(249, 248, 245, 255)),
    AssetPreset("mockup_poster", (2000, 2800), padding=0.18, background=(245, 245, 245, 255)),
    AssetPreset("mockup_sticker", (1600, 1600), padding=0.20, background=(252, 252, 252, 255)),
    AssetPreset("mockup_sign", (2400, 1600), padding=0.14, background=(33, 33, 33, 255)),
)


def clamp(value: float, minimum: int = 0, maximum: int = 255) -> int:
    """색상 계산 중 범위를 벗어나는 값을 0~255 안으로 고정한다."""
    return max(minimum, min(maximum, int(round(value))))


def sanitize_name(value: str, fallback: str = "brandlogo") -> str:
    """파일명/폴더명에 쓰기 어려운 문자를 안전한 문자로 바꾼다."""
    cleaned = re.sub(INVALID_FILENAME_CHARS, "_", value.strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._ ")
    return cleaned or fallback


def resource_path(relative_path: str) -> Path:
    """개발 실행과 PyInstaller exe 실행 모두에서 공통으로 쓸 리소스 경로를 만든다."""
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / relative_path  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / relative_path


def is_valid_hex_color(value: str) -> bool:
    return bool(re.fullmatch(r"#?[0-9A-Fa-f]{6}", value.strip()))


def normalize_hex_color(value: str) -> str:
    value = value.strip().upper()
    if not value.startswith("#"):
        value = f"#{value}"
    return value


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = normalize_hex_color(value)
    return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))


def build_output_name(base_name: str, suffix: str, date_text: str) -> str:
    return f"{base_name}_{date_text}_{suffix}.png"


def build_sized_output_name(
    base_name: str,
    stem: str,
    variant_key: str,
    size: tuple[int, int],
    date_text: str,
) -> str:
    """용도별 리사이즈 파일명을 일관된 형식으로 만든다."""
    width, height = size
    variant_label = VARIANT_FILENAME_LABELS[variant_key]
    parts = [base_name, date_text, stem]
    if variant_label:
        parts.append(variant_label)
    parts.append(f"{width}x{height}")
    return "_".join(parts) + ".png"


def build_canvas_output_name(
    base_name: str,
    stem: str,
    size: tuple[int, int],
    date_text: str,
) -> str:
    """색상 라벨 없이 프리셋 캔버스 이름만 필요한 경우에 사용한다."""
    width, height = size
    return f"{base_name}_{date_text}_{stem}_{width}x{height}.png"


def color_distance(rgb_a: tuple[int, int, int], rgb_b: tuple[int, int, int]) -> int:
    """배경 유사도 판정에 쓸 단순 거리값이다."""
    return max(abs(rgb_a[0] - rgb_b[0]), abs(rgb_a[1] - rgb_b[1]), abs(rgb_a[2] - rgb_b[2]))


def collect_edge_samples(image: Image.Image) -> list[tuple[int, int, int, int]]:
    """가장자리 픽셀을 모아 배경색 후보를 추정한다."""
    width, height = image.size
    pixels = image.load()
    samples: list[tuple[int, int, int, int]] = []

    if width == 0 or height == 0:
        return samples

    step = max(1, min(width, height) // 200)
    coordinates: set[tuple[int, int]] = set()

    for x in range(0, width, step):
        coordinates.add((x, 0))
        coordinates.add((x, height - 1))

    for y in range(0, height, step):
        coordinates.add((0, y))
        coordinates.add((width - 1, y))

    for x, y in coordinates:
        rgba = pixels[x, y]
        if rgba[3] < 8:
            continue
        samples.append(rgba)

    return samples


def detect_background_color(image: Image.Image) -> tuple[int, int, int] | None:
    """
    가장자리에서 가장 많이 보이는 색을 배경색 후보로 잡는다.
    흰색/단색 배경 PNG에서 비교적 안정적으로 동작하는 단순한 방식이다.
    """
    samples = collect_edge_samples(image)
    if not samples:
        return None

    buckets: Counter[tuple[int, int, int]] = Counter()
    grouped: dict[tuple[int, int, int], list[tuple[int, int, int]]] = {}

    for red, green, blue, _alpha in samples:
        bucket = (red // 16, green // 16, blue // 16)
        buckets[bucket] += 1
        grouped.setdefault(bucket, []).append((red, green, blue))

    dominant_bucket, _count = buckets.most_common(1)[0]
    group = grouped[dominant_bucket]

    avg_red = sum(color[0] for color in group) / len(group)
    avg_green = sum(color[1] for color in group) / len(group)
    avg_blue = sum(color[2] for color in group) / len(group)
    return clamp(avg_red), clamp(avg_green), clamp(avg_blue)


def estimate_background_threshold(
    samples: list[tuple[int, int, int, int]],
    background_color: tuple[int, int, int],
) -> int:
    """
    가장자리 샘플 분포에 따라 배경 유사도 기준을 조금 조절한다.
    배경색이 거의 단색이면 더 엄격하게, 약간 흔들리면 조금 여유를 준다.
    """
    distances = [
        color_distance((red, green, blue), background_color)
        for red, green, blue, alpha in samples
        if alpha >= 8
    ]

    if not distances:
        return 40

    distances.sort()
    pivot_index = min(len(distances) - 1, int(len(distances) * 0.7))
    pivot = distances[pivot_index]
    return max(20, min(72, pivot + 12))


def build_background_mask(
    image: Image.Image,
    background_color: tuple[int, int, int],
    threshold: int,
) -> Image.Image:
    """
    가장자리에서 시작해 배경색과 비슷한 픽셀만 따라가며 제거 후보 마스크를 만든다.
    덕분에 로고 내부의 흰색 요소가 배경처럼 오인될 가능성을 줄일 수 있다.
    """
    width, height = image.size
    pixels = image.load()
    mask = Image.new("L", (width, height), 255)
    mask_pixels = mask.load()
    visited = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def index(x: int, y: int) -> int:
        return y * width + x

    def should_mark_background(x: int, y: int, seed_mode: bool = False) -> bool:
        red, green, blue, alpha = pixels[x, y]
        if alpha <= 8:
            return True

        distance = color_distance((red, green, blue), background_color)
        local_threshold = threshold + 8 if seed_mode else threshold
        return distance <= local_threshold

    def enqueue_if_background(x: int, y: int, seed_mode: bool = False) -> None:
        idx = index(x, y)
        if visited[idx]:
            return
        if not should_mark_background(x, y, seed_mode):
            return

        visited[idx] = 1
        mask_pixels[x, y] = 0
        queue.append((x, y))

    for x in range(width):
        enqueue_if_background(x, 0, seed_mode=True)
        enqueue_if_background(x, height - 1, seed_mode=True)

    for y in range(height):
        enqueue_if_background(0, y, seed_mode=True)
        enqueue_if_background(width - 1, y, seed_mode=True)

    neighbors = (
        (-1, -1), (0, -1), (1, -1),
        (-1, 0),           (1, 0),
        (-1, 1),  (0, 1),  (1, 1),
    )

    while queue:
        x, y = queue.popleft()
        for dx, dy in neighbors:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                enqueue_if_background(nx, ny)

    blur_radius = max(0.8, min(width, height) / 700)
    return mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))


def clean_edge_colors(
    image: Image.Image,
    alpha_mask: Image.Image,
    background_color: tuple[int, int, int],
) -> Image.Image:
    """
    배경 제거 후 남는 하얀 테두리를 줄이기 위해 가장자리 색을 정리한다.
    완벽한 AI 배경제거는 아니지만, 단색 배경 로고에서는 꽤 자연스럽게 보정된다.
    """
    result = image.copy()
    pixels = result.load()
    alpha_pixels = alpha_mask.load()
    bg_red, bg_green, bg_blue = background_color
    width, height = result.size

    for y in range(height):
        for x in range(width):
            red, green, blue, _alpha = pixels[x, y]
            alpha = alpha_pixels[x, y]

            if alpha <= 5:
                pixels[x, y] = (0, 0, 0, 0)
                continue

            if alpha < 255:
                alpha_ratio = alpha / 255.0
                red = clamp((red - bg_red * (1.0 - alpha_ratio)) / alpha_ratio)
                green = clamp((green - bg_green * (1.0 - alpha_ratio)) / alpha_ratio)
                blue = clamp((blue - bg_blue * (1.0 - alpha_ratio)) / alpha_ratio)

            pixels[x, y] = (red, green, blue, alpha)

    return result


def remove_background(image: Image.Image) -> Image.Image:
    """
    흰색 또는 단색 배경에 가까운 PNG를 투명화한다.
    기존 투명도가 있는 PNG는 그 알파를 최대한 유지하면서 동작한다.
    """
    rgba = image.convert("RGBA")
    background_color = detect_background_color(rgba)

    if background_color is None:
        return rgba.copy()

    samples = collect_edge_samples(rgba)
    threshold = estimate_background_threshold(samples, background_color)
    background_mask = build_background_mask(rgba, background_color, threshold)

    if background_mask.getextrema() == (255, 255):
        return rgba.copy()

    original_alpha = rgba.getchannel("A")
    combined_alpha = ImageChops.multiply(original_alpha, background_mask)
    result = clean_edge_colors(rgba, combined_alpha, background_color)
    result.putalpha(combined_alpha)
    return result


def recolor_with_alpha(image: Image.Image, rgb_color: tuple[int, int, int]) -> Image.Image:
    """투명도는 유지하고 색상만 원하는 단색으로 바꾼다."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    colored = Image.new("RGBA", rgba.size, rgb_color + (255,))
    colored.putalpha(alpha)
    return colored


def create_grayscale(image: Image.Image) -> Image.Image:
    """회색조 버전을 만들되 알파 채널은 그대로 유지한다."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    gray = ImageOps.grayscale(rgba.convert("RGB"))
    return Image.merge("RGBA", (gray, gray, gray, alpha))


def create_inverted(image: Image.Image) -> Image.Image:
    """RGB만 반전하고 투명도는 유지한다."""
    rgba = image.convert("RGBA")
    red, green, blue, alpha = rgba.split()
    inverted_rgb = ImageOps.invert(Image.merge("RGB", (red, green, blue)))
    inv_red, inv_green, inv_blue = inverted_rgb.split()
    return Image.merge("RGBA", (inv_red, inv_green, inv_blue, alpha))


def generate_variants(
    original_image: Image.Image,
    custom_rgb: tuple[int, int, int],
) -> dict[str, Image.Image]:
    """저장에 필요한 파생 이미지를 한 번에 만든다."""
    transparent = remove_background(original_image)
    variants: dict[str, Image.Image] = {
        "transparent": transparent,
        "black": recolor_with_alpha(transparent, (0, 0, 0)),
        "white": recolor_with_alpha(transparent, (255, 255, 255)),
        "grayscale": create_grayscale(transparent),
        "invert": create_inverted(transparent),
        "color_custom": recolor_with_alpha(transparent, custom_rgb),
    }

    for variant_key, rgb_color in FIXED_COLOR_VARIANTS.items():
        variants[variant_key] = recolor_with_alpha(transparent, rgb_color)

    return variants


def crop_visible_area(image: Image.Image) -> Image.Image:
    """로고 주변의 불필요한 빈 여백을 줄여 캔버스 배치 품질을 높인다."""
    rgba = image.convert("RGBA")
    alpha_bbox = rgba.getchannel("A").getbbox()
    if alpha_bbox:
        return rgba.crop(alpha_bbox)
    return rgba


def render_image_to_preset(image: Image.Image, preset: AssetPreset) -> Image.Image:
    """
    용도별 목표 크기에 맞춰 로고를 새 캔버스에 배치한다.
    비율은 유지하고, 필요한 만큼만 확대/축소한다.
    """
    cropped = crop_visible_area(image)
    canvas = Image.new("RGBA", preset.size, preset.background)

    if cropped.width <= 0 or cropped.height <= 0:
        return canvas

    max_width = max(1, int(round(preset.size[0] * (1.0 - preset.padding * 2))))
    max_height = max(1, int(round(preset.size[1] * (1.0 - preset.padding * 2))))
    scale = min(max_width / cropped.width, max_height / cropped.height)

    resized_width = max(1, int(round(cropped.width * scale)))
    resized_height = max(1, int(round(cropped.height * scale)))
    resized = cropped.resize((resized_width, resized_height), Image.Resampling.LANCZOS)

    offset_x = (preset.size[0] - resized_width) // 2
    offset_y = (preset.size[1] - resized_height) // 2
    canvas.alpha_composite(resized, (offset_x, offset_y))
    return canvas


def ensure_folder_tree(
    brand_root: Path,
    practical_selection: set[tuple[str, str]] | None = None,
    *,
    include_mockups: bool = True,
) -> list[Path]:
    """
    문서에 정의한 폴더 구조를 그대로 만든다.
    반환값은 실제로 파일이 들어갈 실사용 폴더 목록이다.
    """
    practical_targets: list[Path] = []
    selected_pairs = (
        set(practical_selection)
        if practical_selection is not None
        else {(top_folder, subfolder) for top_folder, subfolders in PRACTICAL_FOLDER_GROUPS.items() for subfolder in subfolders}
    )

    for _variant_key, folder_parts in ORIGINAL_REFERENCE_FOLDERS.items():
        (brand_root / folder_parts[0] / folder_parts[1]).mkdir(parents=True, exist_ok=True)

    for top_folder, subfolders in PRACTICAL_FOLDER_GROUPS.items():
        for subfolder in subfolders:
            if (top_folder, subfolder) not in selected_pairs:
                continue
            practical_root = brand_root / top_folder / subfolder
            practical_targets.append(practical_root)
            for variant_folder in COMMON_VARIANT_FOLDERS:
                (practical_root / variant_folder).mkdir(parents=True, exist_ok=True)

    if not include_mockups:
        return practical_targets

    (brand_root / "06_목업").mkdir(parents=True, exist_ok=True)
    return practical_targets


def save_png(image: Image.Image, path: Path) -> None:
    """항상 PNG 형식으로 저장한다."""
    image.save(path, format="PNG")


def apply_window_icon(root: tk.Tk) -> None:
    """스크립트 실행과 exe 실행 모두에서 앱 아이콘을 적용한다."""
    png_icon = resource_path("assets/app_icon.png")
    ico_icon = resource_path("assets/app_icon.ico")

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
            root.after(50, lambda: _apply_windows_taskbar_icon(root, ico_icon))


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


def create_brand_asset_package(
    source_png: Path,
    output_root: Path,
    base_name: str,
    custom_hex: str,
    practical_selection: set[tuple[str, str]] | None = None,
    include_mockups: bool = True,
    logger: Callable[[str], None] | None = None,
) -> dict[str, object]:
    """
    GUI 없이도 재사용할 수 있도록 핵심 생성 로직을 별도 함수로 분리했다.
    이 함수 하나만 호출해도 폴더 생성부터 PNG 저장까지 끝난다.
    """
    def log(message: str) -> None:
        if logger:
            logger(message)

    if not source_png.exists():
        raise FileNotFoundError("선택한 PNG 파일을 찾을 수 없습니다.")
    if source_png.suffix.lower() != ".png":
        raise ValueError("PNG 파일만 선택할 수 있습니다.")
    if not output_root.exists() or not output_root.is_dir():
        raise ValueError("출력 폴더를 먼저 선택해주세요.")
    if not is_valid_hex_color(custom_hex):
        raise ValueError("사용자 지정 색상 형식이 올바르지 않습니다. 예: #1B4797")

    safe_base_name = sanitize_name(base_name or source_png.stem)
    date_text = datetime.now().strftime("%Y%m%d")
    brand_root = output_root / safe_base_name
    selected_pairs = (
        set(practical_selection)
        if practical_selection is not None
        else {(top_folder, subfolder) for top_folder, subfolders in PRACTICAL_FOLDER_GROUPS.items() for subfolder in subfolders}
    )

    log(f"브랜드 폴더 생성 위치: {brand_root}")
    practical_targets = ensure_folder_tree(
        brand_root,
        selected_pairs,
        include_mockups=include_mockups,
    )

    try:
        with Image.open(source_png) as opened_image:
            original_image = opened_image.convert("RGBA")
    except UnidentifiedImageError as exc:
        raise ValueError("PNG 파일을 읽을 수 없습니다. 손상된 파일인지 확인해주세요.") from exc

    custom_rgb = hex_to_rgb(custom_hex)
    log("배경 제거 및 파생 이미지 생성 중...")
    variants = generate_variants(original_image, custom_rgb)

    master_paths: dict[str, Path] = {}
    rendered_paths: list[Path] = []
    saved_count = 0

    original_target = brand_root / ORIGINAL_REFERENCE_FOLDERS["original"][0] / ORIGINAL_REFERENCE_FOLDERS["original"][1]
    original_path = original_target / build_output_name(safe_base_name, "original", date_text)
    shutil.copy2(source_png, original_path)
    master_paths["original"] = original_path
    saved_count += 1
    log(f"저장 완료: {original_path}")

    for variant_key, image in variants.items():
        folder_a, folder_b = ORIGINAL_REFERENCE_FOLDERS[variant_key]
        save_path = brand_root / folder_a / folder_b / build_output_name(safe_base_name, variant_key, date_text)
        save_png(image, save_path)
        master_paths[variant_key] = save_path
        saved_count += 1
        log(f"저장 완료: {save_path}")

    transparent_master_root = brand_root / "00_원본" / "투명배경기본형"
    for preset in MASTER_CANVAS_PRESETS:
        rendered = render_image_to_preset(variants["transparent"], preset)
        save_path = transparent_master_root / build_canvas_output_name(
            safe_base_name,
            preset.stem,
            preset.size,
            date_text,
        )
        save_png(rendered, save_path)
        rendered_paths.append(save_path)
        saved_count += 1
        log(f"기준 프리셋 저장 완료: {save_path}")

    # 실사용 폴더에는 용도별 목표 크기로 다시 렌더링한 PNG를 저장한다.
    for practical_root in practical_targets:
        top_folder = practical_root.parent.name
        subfolder = practical_root.name
        presets = PRACTICAL_ASSET_PRESETS.get((top_folder, subfolder), ())
        if not presets:
            continue

        for variant_folder, variant_keys in VARIANT_GROUP_TO_KEYS.items():
            for preset in presets:
                for variant_key in variant_keys:
                    rendered = render_image_to_preset(variants[variant_key], preset)
                    save_path = practical_root / variant_folder / build_sized_output_name(
                        safe_base_name,
                        preset.stem,
                        variant_key,
                        preset.size,
                        date_text,
                    )
                    save_png(rendered, save_path)
                    rendered_paths.append(save_path)
                    saved_count += 1

    mockup_root = brand_root / "06_목업"
    if not include_mockups:
        log(f"?ㅼ궗???대뜑 由ъ궗?댁쫰 ?앹꽦 ?꾨즺: {len(practical_targets)}媛?????대뜑")
        log(f"異붽? 由ъ궗?댁쫰 ?뚯씪 ?? {len(rendered_paths)}")
        return {
            "brand_root": brand_root,
            "safe_base_name": safe_base_name,
            "date_text": date_text,
            "master_paths": master_paths,
            "rendered_paths": rendered_paths,
            "practical_targets": practical_targets,
            "selected_pairs": selected_pairs,
            "include_mockups": include_mockups,
            "saved_count": saved_count,
        }

    for preset in MOCKUP_PRESETS:
        mockup_source = variants["white"] if preset.stem == "mockup_sign" else variants["transparent"]
        rendered = render_image_to_preset(mockup_source, preset)
        save_path = mockup_root / build_canvas_output_name(
            safe_base_name,
            preset.stem,
            preset.size,
            date_text,
        )
        save_png(rendered, save_path)
        rendered_paths.append(save_path)
        saved_count += 1

    log(f"실사용 폴더 리사이즈 생성 완료: {len(practical_targets)}개 대상 폴더")
    log(f"추가 리사이즈 파일 수: {len(rendered_paths)}")

    return {
        "brand_root": brand_root,
        "safe_base_name": safe_base_name,
        "date_text": date_text,
        "master_paths": master_paths,
        "rendered_paths": rendered_paths,
        "practical_targets": practical_targets,
        "selected_pairs": selected_pairs,
        "include_mockups": include_mockups,
        "saved_count": saved_count,
    }


class LogoConverterApp:
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
        self.scope_vars: dict[tuple[str, str], tk.BooleanVar] = {}
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

    def _init_scope_state(self) -> None:
        for top_folder, subfolders in PRACTICAL_FOLDER_GROUPS.items():
            for subfolder in subfolders:
                var = tk.BooleanVar(value=True)
                var.trace_add("write", self._on_scope_changed)
                self.scope_vars[(top_folder, subfolder)] = var

        self.include_mockups_var.trace_add("write", self._on_scope_changed)
        self._update_scope_summary()

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

        header_card = self._create_card(shell, row=0, column=0, columnspan=2, inner_pad=(34, 30))
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

        steps = -int(delta / 120) if abs(delta) >= 120 else (-1 if delta > 0 else 1)
        self.page_canvas.yview_scroll(steps, "units")
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

    def _build_header(self, parent: tk.Frame) -> None:
        parent.grid_columnconfigure(0, weight=3)
        parent.grid_columnconfigure(1, weight=2)

        left = tk.Frame(parent, bg=COLOR_CARD)
        left.grid(row=0, column=0, sticky="nsew")

        brand_row = tk.Frame(left, bg=COLOR_CARD)
        brand_row.pack(anchor="w")

        icon_chip = tk.Frame(
            brand_row,
            bg=COLOR_PRIMARY_SOFT,
            highlightthickness=1,
            highlightbackground="#D7E3F8",
            bd=0,
            padx=10,
            pady=10,
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
                font=("Malgun Gothic", 12, "bold"),
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
            left,
            text=APP_TITLE,
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Malgun Gothic", 24, "bold"),
        ).pack(anchor="w", pady=(18, 8))

        self._text_label(
            left,
            "원본 PNG 하나만 고르면 인쇄, 배달앱, 네이버, 인스타그램, 웹사이트용 파생 PNG를\n"
            "깔끔한 폴더 구조와 용도별 크기로 한 번에 정리합니다.",
            color=COLOR_MUTED,
            wraplength=560,
            bg=COLOR_CARD,
            size=11,
        ).pack(anchor="w")

        right = tk.Frame(parent, bg=COLOR_CARD)
        right.grid(row=0, column=1, sticky="nsew", padx=(28, 0))

        self._build_brand_panel(right)

        self._build_stat_block(right, "생성 방식", "원본 보관 + 용도별 크기 생성")
        self._build_stat_block(right, "색상 버전", "투명배경 / 흑백 / 반전 / 색상변형")
        self._build_stat_block(right, "포인트 컬러", COLOR_PRIMARY)

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
        block = tk.Frame(parent, bg=COLOR_CARD_SOFT, bd=0, highlightthickness=1, highlightbackground=COLOR_BORDER)
        block.pack(fill="x", pady=6)
        tk.Label(
            block,
            text=title,
            bg=COLOR_CARD_SOFT,
            fg=COLOR_MUTED,
            font=("Malgun Gothic", 9, "bold"),
            pady=8,
            padx=14,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            block,
            text=value,
            bg=COLOR_CARD_SOFT,
            fg=COLOR_TEXT,
            font=("Malgun Gothic", 11, "bold"),
            pady=0,
            padx=14,
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

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
        block = tk.Frame(parent, bg=COLOR_CARD)
        block.pack(fill="x", pady=(0, 18))

        tk.Label(
            block,
            text=title,
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Malgun Gothic", 10, "bold"),
        ).pack(anchor="w")

        control = tk.Frame(block, bg=COLOR_CARD)
        control.pack(fill="x", pady=(8, 6))
        control.grid_columnconfigure(0, weight=1)

        entry_box = tk.Frame(
            control,
            bg=COLOR_CARD_SOFT,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_PRIMARY,
            bd=0,
        )
        entry_box.grid(row=0, column=0, sticky="ew")

        entry = tk.Entry(
            entry_box,
            textvariable=variable,
            relief="flat",
            bd=0,
            bg=COLOR_CARD_SOFT,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            font=("Malgun Gothic", 11),
        )
        entry.pack(fill="x", ipady=12, padx=14, pady=4)

        self._create_button(control, button_text, command, kind="outline").grid(row=0, column=1, padx=(12, 0))

        self._text_label(block, helper_text, wraplength=560).pack(anchor="w")
        return entry

    def _create_text_field(
        self,
        parent: tk.Widget,
        *,
        title: str,
        variable: tk.StringVar,
        helper_text: str,
    ) -> tk.Entry:
        block = tk.Frame(parent, bg=COLOR_CARD)
        block.pack(fill="x", pady=(0, 18))

        tk.Label(
            block,
            text=title,
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Malgun Gothic", 10, "bold"),
        ).pack(anchor="w")

        entry_box = tk.Frame(
            block,
            bg=COLOR_CARD_SOFT,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_PRIMARY,
            bd=0,
        )
        entry_box.pack(fill="x", pady=(8, 6))

        entry = tk.Entry(
            entry_box,
            textvariable=variable,
            relief="flat",
            bd=0,
            bg=COLOR_CARD_SOFT,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            font=("Malgun Gothic", 11),
        )
        entry.pack(fill="x", ipady=12, padx=14, pady=4)

        self._text_label(block, helper_text, wraplength=560).pack(anchor="w")
        return entry

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

        path_panel = tk.Frame(
            parent,
            bg=COLOR_CARD_SOFT,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            bd=0,
            padx=16,
            pady=16,
        )
        path_panel.pack(fill="x")

        tk.Label(
            path_panel,
            textvariable=self.final_path_var,
            bg=COLOR_CARD_SOFT,
            fg=COLOR_TEXT,
            font=("Consolas", 10),
            justify="left",
            anchor="w",
            wraplength=340,
        ).pack(fill="x")

        summary_panel = tk.Frame(
            parent,
            bg=COLOR_PRIMARY_SOFT,
            bd=0,
            highlightthickness=1,
            highlightbackground="#D8E4F8",
            padx=16,
            pady=16,
        )
        summary_panel.pack(fill="x", pady=(14, 0))
        tk.Label(
            summary_panel,
            textvariable=self.completed_count_var,
            bg=COLOR_PRIMARY_SOFT,
            fg=COLOR_PRIMARY,
            font=("Malgun Gothic", 10, "bold"),
            anchor="w",
            justify="left",
        ).pack(fill="x")
        tk.Label(
            summary_panel,
            textvariable=self.scope_summary_var,
            bg=COLOR_PRIMARY_SOFT,
            fg=COLOR_PRIMARY,
            font=("Malgun Gothic", 9, "bold"),
            anchor="w",
            justify="left",
            wraplength=340,
        ).pack(fill="x", pady=(6, 0))
        tk.Label(
            summary_panel,
            textvariable=self.result_summary_var,
            bg=COLOR_PRIMARY_SOFT,
            fg=COLOR_TEXT,
            font=("Malgun Gothic", 9),
            anchor="w",
            justify="left",
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
            tk.Label(
                text_wrap,
                text=title,
                bg=COLOR_CARD,
                fg=COLOR_TEXT,
                font=("Malgun Gothic", 10, "bold"),
            ).pack(anchor="w")
            self._text_label(text_wrap, desc, wraplength=290).pack(anchor="w", pady=(2, 0))

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

        tk.Label(
            info,
            text="현재 선택 범위",
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            font=("Malgun Gothic", 9, "bold"),
        ).pack(anchor="w")
        tk.Label(
            info,
            textvariable=self.scope_summary_var,
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=("Malgun Gothic", 11, "bold"),
        ).pack(anchor="w", pady=(4, 2))
        tk.Label(
            info,
            textvariable=self.completed_count_var,
            bg=COLOR_CARD,
            fg=COLOR_PRIMARY,
            font=("Malgun Gothic", 9, "bold"),
        ).pack(anchor="w", pady=(0, 2))
        tk.Label(
            info,
            textvariable=self.status_var,
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            font=("Malgun Gothic", 9),
            justify="left",
            anchor="w",
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

        panel = tk.Frame(parent, bg=COLOR_PRIMARY_SOFT, padx=18, pady=18)
        panel.pack(fill="x")
        tk.Label(
            panel,
            textvariable=self.status_var,
            bg=COLOR_PRIMARY_SOFT,
            fg=COLOR_PRIMARY,
            font=("Malgun Gothic", 11, "bold"),
            justify="left",
            anchor="w",
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

    def _get_selected_practical_pairs(self) -> set[tuple[str, str]]:
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

    def run_generation(self) -> None:
        try:
            source_path, custom_hex = self._validate_form_inputs()
            output_text = self.output_path_var.get().strip()
            if not output_text:
                raise ValueError("출력 폴더를 선택해주세요.")
            output_root = Path(output_text)
            if not output_root.exists():
                raise ValueError("선택한 출력 폴더를 찾을 수 없습니다.")

            base_name = self.base_name_var.get().strip() or source_path.stem
            selected_pairs = self._get_selected_practical_pairs()
            include_mockups = self.include_mockups_var.get()
        except Exception as exc:
            messagebox.showerror("입력 오류", str(exc))
            self._set_status(str(exc))
            return

        self._clear_log()
        self._update_scope_summary()
        self._set_status("자동 생성 작업을 시작합니다...")
        self.root.config(cursor="watch")

        try:
            result = create_brand_asset_package(
                source_png=source_path,
                output_root=output_root,
                base_name=base_name,
                custom_hex=custom_hex,
                practical_selection=selected_pairs,
                include_mockups=include_mockups,
                logger=self._append_log,
            )

            brand_root = result["brand_root"]
            saved_count = result["saved_count"]
            practical_targets = result["practical_targets"]
            self.final_path_var.set(str(brand_root))
            self.completed_count_var.set(f"최근 생성 파일 수: {saved_count}")
            self.result_summary_var.set(
                f"{self._build_scope_summary_text()} 기준으로 생성했습니다. "
                f"실사용 폴더 {len(practical_targets)}개가 저장 경로 안에 정리됩니다."
            )
            self._set_status(
                f"자동 생성 완료. 총 {saved_count}개 파일을 저장했고, "
                f"{len(practical_targets)}개 실사용 폴더에 정리했습니다."
            )
            self._append_log(f"작업 완료 폴더: {brand_root}")
            messagebox.showinfo(
                "생성 완료",
                f"PNG 파생본 생성이 완료되었습니다.\n\n저장 위치:\n{brand_root}\n\n총 저장 파일 수: {saved_count}",
            )
        except Exception as exc:
            traceback_text = traceback.format_exc()
            self._append_log(traceback_text)
            messagebox.showerror("생성 오류", f"파일 생성 중 오류가 발생했습니다.\n\n{exc}")
            self.result_summary_var.set("생성에 실패했습니다. 입력값과 실행 로그를 확인해 주세요.")
            self._set_status("파일 생성 실패. 실행 로그를 확인해주세요.")
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
