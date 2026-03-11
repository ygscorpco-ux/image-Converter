from __future__ import annotations

import re
import shutil
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

try:
    from PIL import Image, ImageChops, ImageFilter, ImageOps, UnidentifiedImageError
except ImportError as exc:  # pragma: no cover - startup guard
    print("Pillow가 설치되어 있지 않습니다. 먼저 'pip install pillow'를 실행해주세요.")
    print(exc)
    raise SystemExit(1)


INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
BACKGROUND_MASK_ANALYSIS_MAX_DIM = 1800
FOREGROUND_DISTANCE_SAMPLE_TARGET = 1200

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


PracticalPair = tuple[str, str]
ALL_PRACTICAL_PAIRS: frozenset[PracticalPair] = frozenset(
    (top_folder, subfolder)
    for top_folder, subfolders in PRACTICAL_FOLDER_GROUPS.items()
    for subfolder in subfolders
)


@dataclass(frozen=True)
class GenerationRequest:
    source_png: Path
    output_root: Path
    base_name: str
    custom_hex: str
    practical_selection: set[PracticalPair]
    include_mockups: bool


@dataclass
class GenerationSummary:
    brand_root: Path
    safe_base_name: str
    date_text: str
    master_paths: dict[str, Path]
    rendered_paths: list[Path]
    practical_targets: list[Path]
    selected_pairs: set[PracticalPair]
    include_mockups: bool

    @property
    def saved_count(self) -> int:
        return len(self.master_paths) + len(self.rendered_paths)


MASTER_CANVAS_PRESETS = (
    AssetPreset("square_master", (3000, 3000), padding=0.14),
    AssetPreset("horizontal_master", (3000, 1800), padding=0.10),
    AssetPreset("vertical_master", (3000, 3750), padding=0.14),
)

PRACTICAL_ASSET_PRESETS: dict[PracticalPair, tuple[AssetPreset, ...]] = {
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


def resize_for_background_analysis(image: Image.Image) -> tuple[Image.Image, float]:
    """
    아주 큰 원본은 축소본으로 배경 마스크를 먼저 계산하고,
    최종 마스크만 원본 크기로 다시 올려 속도를 크게 줄인다.
    """
    width, height = image.size
    max_dim = max(width, height)
    if max_dim <= BACKGROUND_MASK_ANALYSIS_MAX_DIM:
        return image, 1.0

    scale = BACKGROUND_MASK_ANALYSIS_MAX_DIM / max_dim
    resized = image.resize(
        (
            max(1, round(width * scale)),
            max(1, round(height * scale)),
        ),
        Image.Resampling.BILINEAR,
    )
    return resized, scale


def build_background_mask(
    image: Image.Image,
    background_color: tuple[int, int, int],
    threshold: int,
) -> Image.Image:
    """
    가장자리에서 시작해 배경색과 비슷한 픽셀만 따라가며 제거 후보 마스크를 만든다.
    덕분에 로고 내부의 흰색 요소가 배경처럼 오인될 가능성을 줄일 수 있다.
    """
    original_size = image.size
    work_image, scale = resize_for_background_analysis(image)
    width, height = work_image.size
    pixels = work_image.load()
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
    blurred_mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    if scale == 1.0:
        return blurred_mask

    upscaled_mask = blurred_mask.resize(original_size, Image.Resampling.BICUBIC)
    final_blur = min(1.6, max(0.7, (1.0 / scale) * 0.18))
    return upscaled_mask.filter(ImageFilter.GaussianBlur(radius=final_blur))


def pick_percentile(values: list[int], percentile: float) -> int:
    """작은 표본에서도 안정적으로 분위값을 뽑기 위한 단순 helper."""
    if not values:
        return 0

    ordered = sorted(values)
    index = int((len(ordered) - 1) * percentile)
    index = max(0, min(len(ordered) - 1, index))
    return ordered[index]


def estimate_foreground_distance_scale(
    image: Image.Image,
    background_color: tuple[int, int, int],
    threshold: int,
) -> int:
    """
    배경과 충분히 다른 전경 픽셀들의 거리 분포를 보고
    가장자리 알파를 얼마나 강하게 줄일지 기준값을 정한다.
    """
    pixels = image.load()
    width, height = image.size
    distances: list[int] = []
    sample_step = max(1, round(max(width, height) / FOREGROUND_DISTANCE_SAMPLE_TARGET))

    for y in range(0, height, sample_step):
        for x in range(0, width, sample_step):
            red, green, blue, alpha = pixels[x, y]
            if alpha < 24:
                continue

            distance = color_distance((red, green, blue), background_color)
            if distance <= threshold:
                continue

            distances.append(distance)

    if not distances:
        return max(48, threshold * 2)

    return max(threshold + 12, pick_percentile(distances, 0.98))


def refine_edge_alpha(
    image: Image.Image,
    alpha_mask: Image.Image,
    background_mask: Image.Image,
    background_color: tuple[int, int, int],
    threshold: int,
) -> Image.Image:
    """
    단색 배경 로고의 안티앨리어싱 가장자리에서 흰 테두리가 남지 않도록
    경계 구간에 한해 색 거리 기반으로 알파를 한 번 더 조인다.
    """
    refined = alpha_mask.copy()
    refined_pixels = refined.load()
    alpha_pixels = alpha_mask.load()
    edge_zone = background_mask.filter(ImageFilter.MinFilter(5))
    edge_pixels = edge_zone.load()
    pixels = image.load()
    distance_scale = estimate_foreground_distance_scale(image, background_color, threshold)
    edge_bbox = edge_zone.point(lambda value: 255 if value < 250 else 0).getbbox()

    if not edge_bbox:
        return refined

    left, upper, right, lower = edge_bbox

    for y in range(upper, lower):
        for x in range(left, right):
            current_alpha = alpha_pixels[x, y]
            if current_alpha <= 5:
                refined_pixels[x, y] = 0
                continue

            if current_alpha >= 245:
                refined_pixels[x, y] = current_alpha
                continue

            # 침식된 마스크에서 완전히 남아 있는 내부 영역은 기존 알파를 유지한다.
            if edge_pixels[x, y] >= 250:
                refined_pixels[x, y] = current_alpha
                continue

            red, green, blue, source_alpha = pixels[x, y]
            if source_alpha <= 8:
                refined_pixels[x, y] = 0
                continue

            distance = color_distance((red, green, blue), background_color)
            distance_alpha = clamp(distance * 255 / max(1, distance_scale))
            refined_pixels[x, y] = min(current_alpha, distance_alpha)

    return refined


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
    alpha_bbox = alpha_mask.point(lambda value: 255 if 5 < value < 255 else 0).getbbox()

    if not alpha_bbox:
        return result

    left, upper, right, lower = alpha_bbox

    for y in range(upper, lower):
        for x in range(left, right):
            red, green, blue, _alpha = pixels[x, y]
            alpha = alpha_pixels[x, y]

            if alpha <= 5:
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
    combined_alpha = refine_edge_alpha(
        rgba,
        combined_alpha,
        background_mask,
        background_color,
        threshold,
    )
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


def resolve_practical_selection(
    practical_selection: set[PracticalPair] | None,
) -> set[PracticalPair]:
    if practical_selection is None:
        return set(ALL_PRACTICAL_PAIRS)
    return set(practical_selection)


def get_original_reference_dir(brand_root: Path, variant_key: str) -> Path:
    folder_a, folder_b = ORIGINAL_REFERENCE_FOLDERS[variant_key]
    return brand_root / folder_a / folder_b


def load_png_image(source_png: Path) -> Image.Image:
    try:
        with Image.open(source_png) as opened_image:
            return opened_image.convert("RGBA")
    except UnidentifiedImageError as exc:
        raise ValueError("PNG 파일을 읽을 수 없습니다. 손상된 파일인지 확인해주세요.") from exc


def save_png(image: Image.Image, path: Path) -> None:
    """항상 PNG 형식으로 저장한다."""
    image.save(path, format="PNG")


def save_original_reference_assets(
    source_png: Path,
    brand_root: Path,
    safe_base_name: str,
    date_text: str,
    variants: dict[str, Image.Image],
    log: Callable[[str], None],
) -> tuple[dict[str, Path], list[Path]]:
    master_paths: dict[str, Path] = {}
    rendered_paths: list[Path] = []

    original_target = get_original_reference_dir(brand_root, "original")
    original_path = original_target / build_output_name(safe_base_name, "original", date_text)
    shutil.copy2(source_png, original_path)
    master_paths["original"] = original_path
    log(f"저장 완료: {original_path}")

    for variant_key, image in variants.items():
        save_path = get_original_reference_dir(brand_root, variant_key) / build_output_name(
            safe_base_name,
            variant_key,
            date_text,
        )
        save_png(image, save_path)
        master_paths[variant_key] = save_path
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
        log(f"기준 프리셋 저장 완료: {save_path}")

    return master_paths, rendered_paths


def render_practical_assets(
    practical_targets: list[Path],
    variants: dict[str, Image.Image],
    safe_base_name: str,
    date_text: str,
) -> list[Path]:
    rendered_paths: list[Path] = []

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

    return rendered_paths


def render_mockup_assets(
    brand_root: Path,
    variants: dict[str, Image.Image],
    safe_base_name: str,
    date_text: str,
) -> list[Path]:
    rendered_paths: list[Path] = []
    mockup_root = brand_root / "06_목업"

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

    return rendered_paths


def ensure_folder_tree(
    brand_root: Path,
    practical_selection: set[PracticalPair] | None = None,
    *,
    include_mockups: bool = True,
) -> list[Path]:
    """
    문서에 정의한 폴더 구조를 그대로 만든다.
    반환값은 실제로 파일이 들어갈 실사용 폴더 목록이다.
    """
    practical_targets: list[Path] = []
    selected_pairs = resolve_practical_selection(practical_selection)

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

    if include_mockups:
        (brand_root / "06_목업").mkdir(parents=True, exist_ok=True)
    return practical_targets


def create_brand_asset_package(
    source_png: Path,
    output_root: Path,
    base_name: str,
    custom_hex: str,
    practical_selection: set[PracticalPair] | None = None,
    include_mockups: bool = True,
    logger: Callable[[str], None] | None = None,
) -> GenerationSummary:
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
    selected_pairs = resolve_practical_selection(practical_selection)

    log(f"브랜드 폴더 생성 위치: {brand_root}")
    practical_targets = ensure_folder_tree(
        brand_root,
        selected_pairs,
        include_mockups=include_mockups,
    )

    original_image = load_png_image(source_png)
    custom_rgb = hex_to_rgb(custom_hex)
    log("배경 제거 및 파생 이미지 생성 중...")
    variants = generate_variants(original_image, custom_rgb)

    master_paths, rendered_paths = save_original_reference_assets(
        source_png=source_png,
        brand_root=brand_root,
        safe_base_name=safe_base_name,
        date_text=date_text,
        variants=variants,
        log=log,
    )
    rendered_paths.extend(
        render_practical_assets(
            practical_targets=practical_targets,
            variants=variants,
            safe_base_name=safe_base_name,
            date_text=date_text,
        )
    )

    if include_mockups:
        rendered_paths.extend(
            render_mockup_assets(
                brand_root=brand_root,
                variants=variants,
                safe_base_name=safe_base_name,
                date_text=date_text,
            )
        )

    summary = GenerationSummary(
        brand_root=brand_root,
        safe_base_name=safe_base_name,
        date_text=date_text,
        master_paths=master_paths,
        rendered_paths=rendered_paths,
        practical_targets=practical_targets,
        selected_pairs=selected_pairs,
        include_mockups=include_mockups,
    )
    log(f"실사용 폴더 리사이즈 생성 완료: {len(summary.practical_targets)}개 대상 폴더")
    log(f"추가 리사이즈 파일 수: {len(summary.rendered_paths)}")
    return summary


__all__ = [
    "GenerationRequest",
    "GenerationSummary",
    "PracticalPair",
    "PRACTICAL_FOLDER_GROUPS",
    "sanitize_name",
    "is_valid_hex_color",
    "normalize_hex_color",
    "create_brand_asset_package",
]
