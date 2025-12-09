from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import base64
import logging
import os
import cv2
import numpy as np
import easyocr
import threading
import time
import platform
import requests
import functools
from spellchecker import SpellChecker


spellchecker = SpellChecker()

# Fix for PIL.ANTIALIAS deprecation in EasyOCR
# Pillow 10.0.0+ removed ANTIALIAS, use LANCZOS instead
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize EasyOCR reader (lazy loading - will load on first use)
easyocr_reader = None

# Minimum confidence threshold for accepting OCR detections
MIN_CONFIDENCE = 0.1
HIGH_CONFIDENCE_THRESHOLD = 0.95

# Ranking preferences: original EasyOCR output tends to preserve characters better
# than heavily processed variants, so we boost its score slightly during selection.
CONFIG_PRIORITY = {
    "original_easyocr": 3,
    "resized_easyocr": 2,
}
DEFAULT_CONFIG_PRIORITY = 1
CONFIG_PRIORITY_WEIGHT = 4.0
WORD_FREQUENCY_WEIGHT = 6.0  # boosts candidates whose words appear consistently across configs
FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

ENGLISH_TO_CHINESE_PUNCT = {
    ',': '，',
    '.': '。',  # period to full stop
    '!': '！',
    '?': '？',
    ':': '：',
    ';': '；',
    '(': '（',
    ')': '）',
    '[': '【',
    ']': '】'
}
CHINESE_TO_ENGLISH_PUNCT = {v: k for k, v in ENGLISH_TO_CHINESE_PUNCT.items()}
CHINESE_CHAR_RANGES = [
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs
    (0x3400, 0x4DBF),   # CJK Extension A
    (0x20000, 0x2A6DF)  # CJK Extension B
]


def is_english_alnum(char):
    return char.isascii() and char.isalnum()


def is_chinese_char(char):
    code_point = ord(char)
    for start, end in CHINESE_CHAR_RANGES:
        if start <= code_point <= end:
            return True
    return False


def normalize_punctuation_by_language(text):
    """Ensure punctuation style matches surrounding language (English vs. Chinese)."""
    if not text:
        return text

    chars = list(text)
    length = len(chars)

    def context_flags(index):
        """Check nearest non-space chars to determine language context."""
        english = False
        chinese = False

        for direction in (-1, 1):
            j = index + direction
            while 0 <= j < length:
                candidate = chars[j]
                if candidate.isspace():
                    j += direction
                    continue
                if is_english_alnum(candidate):
                    english = True
                elif is_chinese_char(candidate):
                    chinese = True
                break
        return english, chinese

    for i, ch in enumerate(chars):
        if ch not in CHINESE_TO_ENGLISH_PUNCT and ch not in ENGLISH_TO_CHINESE_PUNCT:
            continue

        english_ctx, chinese_ctx = context_flags(i)

        if english_ctx and not chinese_ctx:
            chars[i] = CHINESE_TO_ENGLISH_PUNCT.get(ch, ch)
        elif chinese_ctx and not english_ctx:
            chars[i] = ENGLISH_TO_CHINESE_PUNCT.get(ch, ch)
        # If both or neither context detected, leave punctuation as-is.

    return ''.join(chars)


def get_config_priority(config_name):
    """Return ranking weight for a given OCR configuration."""
    if not config_name:
        return DEFAULT_CONFIG_PRIORITY
    if config_name in CONFIG_PRIORITY:
        return CONFIG_PRIORITY[config_name]
    if config_name.startswith("preprocess_"):
        return 1
    return DEFAULT_CONFIG_PRIORITY

def check_gpu_available():
    """Check if GPU acceleration is available (CUDA for NVIDIA, MPS for Apple Silicon)"""
    try:
        import torch
        system = platform.system()
        
        # Check for CUDA (NVIDIA GPUs)
        if torch.cuda.is_available():
            logger.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
            return True
        
        # Check for Metal Performance Shaders (Apple Silicon Macs)
        elif system == "Darwin" and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("Metal Performance Shaders (MPS) available for Apple Silicon GPU")
            return True
        else:
            if system == "Darwin":
                logger.info("macOS detected but MPS not available, will use CPU")
            else:
                logger.info("CUDA not available, will use CPU")
            return False
    except ImportError:
        logger.info("PyTorch not found, will attempt GPU detection via EasyOCR")
        return None  # Let EasyOCR handle it
    except Exception as e:
        logger.warning(f"Error checking GPU availability: {e}, will use CPU")
        return False

def get_easyocr_reader():
    """Lazy load EasyOCR reader to avoid slow startup"""
    global easyocr_reader
    if easyocr_reader is None:
        logger.info("Initializing EasyOCR reader (first time, may take a moment)...")

        # Languages: English + Simplified Chinese
        # NOTE: EasyOCR's Traditional Chinese model (`ch_tra`) cannot be combined
        # with other Chinese languages in this version and was causing:
        # "Chinese_tra is only compatible with English, try lang_list=['ch_tra','en']"
        # To keep things stable, we use English + Simplified Chinese only here.
        languages = ['en', 'ch_sim']

        # Check GPU availability
        use_gpu = check_gpu_available()

        # Try GPU first if available, fallback to CPU
        if use_gpu is True:
            try:
                logger.info("Attempting to initialize EasyOCR with GPU (en + ch_sim)...")
                easyocr_reader = easyocr.Reader(languages, gpu=True)
                logger.info("EasyOCR reader initialized successfully with GPU (English + Simplified Chinese)")
            except Exception as e:
                logger.warning(f"Failed to initialize EasyOCR with GPU (en + ch_sim): {e}")
                logger.info("Falling back to CPU...")
                try:
                    easyocr_reader = easyocr.Reader(languages, gpu=False)
                    logger.info("EasyOCR reader initialized successfully with CPU (English + Simplified Chinese)")
                except Exception as e2:
                    logger.error(f"Failed to initialize EasyOCR with CPU: {e2}")
        elif use_gpu is None:
            # Try GPU first, let EasyOCR handle detection
            try:
                logger.info("Attempting to initialize EasyOCR with GPU (auto-detect, en + ch_sim)...")
                easyocr_reader = easyocr.Reader(languages, gpu=True)
                logger.info("EasyOCR reader initialized successfully (English + Simplified Chinese)")
            except Exception as e:
                logger.warning(f"Failed to initialize EasyOCR with GPU (auto-detect, en + ch_sim): {e}")
                logger.info("Falling back to CPU...")
                try:
                    easyocr_reader = easyocr.Reader(languages, gpu=False)
                    logger.info("EasyOCR reader initialized successfully with CPU (English + Simplified Chinese)")
                except Exception as e2:
                    logger.error(f"Failed to initialize EasyOCR with CPU: {e2}")
        else:
            # Use CPU
            try:
                easyocr_reader = easyocr.Reader(languages, gpu=False)
                logger.info("EasyOCR reader initialized successfully with CPU (English + Simplified + Traditional Chinese)")
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR with CPU (en + ch_sim): {e}")
    return easyocr_reader

def run_with_timeout(func, timeout_seconds=15, default_return=None):
    """Run a function with a timeout. Returns default_return if timeout."""
    result = [default_return]
    exception = [None]
    
    def target():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        logger.warning(f"Function {func.__name__ if hasattr(func, '__name__') else 'unknown'} timed out after {timeout_seconds}s")
        return default_return
    
    if exception[0]:
        raise exception[0]
    
    return result[0]

def release_gpu_memory():
    """釋放 PyTorch GPU 記憶體（MPS/CUDA）"""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        if hasattr(torch, 'mps') and hasattr(torch.mps, 'empty_cache'):
            torch.mps.empty_cache()
    except Exception as e:
        logger.warning(f"Failed to release GPU memory: {e}")

def translate_text_with_deepl(text, target_lang="ZH"):
    """
    使用 DeepL API 進行翻譯。
    text: 原文
    target_lang: 目標語言（如 ZH, EN, JA...）
    """
    api_key = os.getenv("DEEPL_API_KEY")
    if not api_key:
        logger.error("DEEPL_API_KEY not set in environment variables.")
        return None
    url = "https://api-free.deepl.com/v2/translate"
    data = {
        "auth_key": api_key,
        "text": text,
        "target_lang": target_lang
    }
    try:
        resp = requests.post(url, data=data, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        if "translations" in result and result["translations"]:
            return result["translations"][0]["text"]
        else:
            logger.error(f"DeepL API returned no translations: {result}")
            return None
    except Exception as e:
        logger.error(f"DeepL API translation failed: {e}")
        return None


@functools.lru_cache(maxsize=16)
def load_overlay_font(size):
    """Try to load a TTF font that supports multilingual glyphs."""
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def bbox_to_rect(bbox):
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)
    return {
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "mid_y": (y_min + y_max) / 2.0,
        "height": max(1.0, y_max - y_min),
        "width": max(1.0, x_max - x_min),
    }


def should_merge_vertical(upper, lower):
    if upper["y_min"] > lower["y_min"]:
        upper, lower = lower, upper

    x_overlap = min(upper["x_max"], lower["x_max"]) - max(upper["x_min"], lower["x_min"])
    if x_overlap <= 0:
        return False

    width_min = min(upper["width"], lower["width"])
    overlap_ratio = x_overlap / max(1.0, width_min)
    height_ratio = min(upper["height"], lower["height"]) / max(1.0, max(upper["height"], lower["height"]))

    overlap_threshold = 0.65 if height_ratio < 0.6 else 0.45
    if overlap_ratio < overlap_threshold:
        return False

    vertical_gap = lower["y_min"] - upper["y_max"]
    min_gap = 10
    max_gap = min(12, max(upper["height"], lower["height"]) * 0.3)

    if vertical_gap < 0:
        return True
    if vertical_gap < min_gap:
        return True
    if vertical_gap > max_gap:
        return False

    return True
def merge_segments_into_lines(segments):
    """
    Group OCR segments into logical text lines with adaptive vertical merging.
    """
    if not segments:
        return []

    # Convert to rect structure and clean
    processed = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        bbox = seg.get("bbox")
        if not text or not bbox or len(bbox) != 4:
            continue

        rect = bbox_to_rect(bbox)
        seg = seg.copy()
        seg["_rect"] = rect
        processed.append(seg)

    # Sort top-to-bottom, then left-to-right
    processed.sort(key=lambda s: (s["_rect"]["y_min"], s["_rect"]["x_min"]))

    # -------------------------------------------------------------------------
    # PHASE 1: Merge into horizontal line chunks
    # -------------------------------------------------------------------------
    lines = []
    for seg in processed:
        r = seg["_rect"]
        placed = False

        for line in lines:
            lr = line["rect"]

            # Same line if mid-Y close
            same_row = abs(r["mid_y"] - lr["mid_y"]) <= max(r["height"], lr["height"]) * 0.60

            # And x is close (avoid merging far-right bubbles)
            horizontal_gap = r["x_min"] - lr["x_max"]
            if same_row and horizontal_gap <= 40:
                line["segments"].append(seg)

                # Update union bounding box
                lr["x_min"] = min(lr["x_min"], r["x_min"])
                lr["x_max"] = max(lr["x_max"], r["x_max"])
                lr["y_min"] = min(lr["y_min"], r["y_min"])
                lr["y_max"] = max(lr["y_max"], r["y_max"])
                lr["width"] = lr["x_max"] - lr["x_min"]
                lr["height"] = lr["y_max"] - lr["y_min"]
                lr["mid_y"] = (lr["y_min"] + lr["y_max"]) / 2
                placed = True
                break

        if not placed:
            lines.append({
                "segments": [seg],
                "rect": r.copy()
            })

    # Sort again by vertical position
    lines.sort(key=lambda L: L["rect"]["y_min"])

    # -------------------------------------------------------------------------
    # PHASE 2: ADAPTIVE VERTICAL MERGING (title vs subtitle separation)
    # -------------------------------------------------------------------------
    merged = []
    for line in lines:
        if not merged:
            merged.append(line)
            continue

        prev = merged[-1]
        prev_r = prev["rect"]
        curr_r = line["rect"]

        if should_merge_vertical(prev_r, curr_r):
            # Merge the two vertical blocks
            prev["segments"].extend(line["segments"])
            prev_r["x_min"] = min(prev_r["x_min"], curr_r["x_min"])
            prev_r["x_max"] = max(prev_r["x_max"], curr_r["x_max"])
            prev_r["y_min"] = min(prev_r["y_min"], curr_r["y_min"])
            prev_r["y_max"] = max(prev_r["y_max"], curr_r["y_max"])
            prev_r["width"] = prev_r["x_max"] - prev_r["x_min"]
            prev_r["height"] = prev_r["y_max"] - prev_r["y_min"]
            prev_r["mid_y"] = (prev_r["y_min"] + prev_r["y_max"]) / 2

        else:
            merged.append(line)

    # -------------------------------------------------------------------------
    # PHASE 3: Build output format
    # -------------------------------------------------------------------------
    output = []
    for line in merged:
        segs = sorted(
            line["segments"],
            key=lambda s: (s["_rect"]["y_min"], s["_rect"]["x_min"])
        )
        if not segs:
            continue

        # Reconstruct text with line breaks but without extra structured metadata
        lines_text = []
        current_line = []
        current_y = segs[0]["_rect"]["mid_y"]
        line_gap_threshold = max(8, line["rect"]["height"] * 0.35)

        for seg in segs:
            rect = seg["_rect"]
            if abs(rect["mid_y"] - current_y) > line_gap_threshold and current_line:
                lines_text.append(" ".join(current_line).strip())
                current_line = []
            current_line.append(seg["text"])
            current_y = rect["mid_y"]

        if current_line:
            lines_text.append(" ".join(current_line).strip())

        clean_text = "\n".join(filter(None, lines_text)).strip()
        if not clean_text:
            continue

        r = line["rect"]
        avg_conf = sum(s.get("confidence", 0) for s in segs) / max(1, len(segs))

        output.append({
            "text": clean_text,
            "bbox": [
                [r["x_min"], r["y_min"]],
                [r["x_max"], r["y_min"]],
                [r["x_max"], r["y_max"]],
                [r["x_min"], r["y_max"]]
            ],
            "confidence": avg_conf,
            "children": [{k: v for k, v in s.items() if k != "_rect"} for s in segs]
        })

    return output

def translate_segment_lines(segments, target_lang):
    """Translate grouped line segments for better context."""
    merged_lines = merge_segments_into_lines(segments)
    translated = []
    for line in merged_lines:
        text = line.get("text", "").strip()
        if not text:
            continue
        translated_text = translate_text_with_deepl(text, target_lang)
        line_copy = line.copy()
        if translated_text:
            line_copy["translated_text"] = translated_text
        else:
            line_copy["translated_text"] = None
            line_copy["translation_error"] = "Translation failed or returned empty text."
        translated.append(line_copy)
    return translated


def render_translated_overlay(img, line_segments, boxes_only=False):
    """Draw overlays (optionally with translated text) on top of the original image and return base64 PNG."""
    if not line_segments:
        return None
    
    annotated = img.convert("RGBA").copy()
    draw = ImageDraw.Draw(annotated, "RGBA")
    
    def measure_text(line, font):
        try:
            tb = draw.textbbox((0, 0), line, font=font)
            return tb[2] - tb[0], tb[3] - tb[1]
        except Exception:
            return draw.textsize(line, font=font)
    
    def wrap_text_to_width(text, font, max_width):
        words = text.split()
        if not words:
            return [text]
        lines = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if measure_text(candidate, font)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        
        # Handle words that are still too wide by splitting into characters
        final_lines = []
        for line in lines:
            if measure_text(line, font)[0] <= max_width:
                final_lines.append(line)
                continue
            buffer = ""
            for ch in line:
                candidate = buffer + ch
                if measure_text(candidate, font)[0] <= max_width:
                    buffer = candidate
                else:
                    if buffer:
                        final_lines.append(buffer)
                    buffer = ch
            if buffer:
                final_lines.append(buffer)
        return final_lines
    
    for seg in line_segments:
        translation = None if boxes_only else seg.get("translated_text")
        bbox = seg.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        
        # Normalize bbox points
        try:
            points = [(int(p[0]), int(p[1])) for p in bbox]
        except Exception:
            continue
        
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        box_height = max(20, y_max - y_min)
        box_width = max(20, x_max - x_min)
        padding = max(4, int(min(box_height, box_width) * 0.05))
        
        max_text_width = box_width - 2 * padding
        max_text_height = box_height - 2 * padding
        
        
        if boxes_only or not translation:
            continue
        
        text_lines = []
        font = None
        for size in range(int(min(64, box_height * 0.9)), 5, -2):
            candidate_font = load_overlay_font(size)
            lines = wrap_text_to_width(translation, candidate_font, max_text_width)
            line_height = measure_text("Ag", candidate_font)[1]
            total_height = len(lines) * line_height + max(0, len(lines) - 1) * 2
            if total_height <= max_text_height:
                font = candidate_font
                text_lines = lines
                line_spacing = 2
                break
        if not font:
            font = load_overlay_font(6)
            text_lines = wrap_text_to_width(translation, font, max_text_width)
            line_spacing = 2
        
        # Improved background color detection - sample from edges and corners to avoid text
        img_rgb = img.convert("RGB")
        
        # Expand sampling area slightly beyond the text box to get background
        # Use a small margin to avoid pulling distant colors that do not represent the box area
        expand_margin = max(4, min(box_width, box_height) // 6)
        sample_area_x_min = max(0, x_min - expand_margin)
        sample_area_x_max = min(img_rgb.width, x_max + expand_margin)
        sample_area_y_min = max(0, y_min - expand_margin)
        sample_area_y_max = min(img_rgb.height, y_max + expand_margin)
        
        # Sample from edges and corners (avoiding center where text likely is)
        sample_points = []
        
        # Top edge (avoid center)
        if sample_area_y_min < y_min:
            for x in [sample_area_x_min, sample_area_x_min + (sample_area_x_max - sample_area_x_min) // 4,
                     sample_area_x_min + 3 * (sample_area_x_max - sample_area_x_min) // 4, sample_area_x_max - 1]:
                if 0 <= x < img_rgb.width and 0 <= sample_area_y_min < img_rgb.height:
                    sample_points.append((x, sample_area_y_min))
        
        # Bottom edge
        if sample_area_y_max > y_max:
            for x in [sample_area_x_min, sample_area_x_min + (sample_area_x_max - sample_area_x_min) // 4,
                     sample_area_x_min + 3 * (sample_area_x_max - sample_area_x_min) // 4, sample_area_x_max - 1]:
                if 0 <= x < img_rgb.width and 0 <= sample_area_y_max - 1 < img_rgb.height:
                    sample_points.append((x, sample_area_y_max - 1))
        
        # Left edge
        if sample_area_x_min < x_min:
            for y in [sample_area_y_min, sample_area_y_min + (sample_area_y_max - sample_area_y_min) // 4,
                     sample_area_y_min + 3 * (sample_area_y_max - sample_area_y_min) // 4, sample_area_y_max - 1]:
                if 0 <= sample_area_x_min < img_rgb.width and 0 <= y < img_rgb.height:
                    sample_points.append((sample_area_x_min, y))
        
        # Right edge
        if sample_area_x_max > x_max:
            for y in [sample_area_y_min, sample_area_y_min + (sample_area_y_max - sample_area_y_min) // 4,
                     sample_area_y_min + 3 * (sample_area_y_max - sample_area_y_min) // 4, sample_area_y_max - 1]:
                if 0 <= sample_area_x_max - 1 < img_rgb.width and 0 <= y < img_rgb.height:
                    sample_points.append((sample_area_x_max - 1, y))
        
        # If we don't have enough edge samples, add corner samples
        if len(sample_points) < 4:
            corners = [
                (sample_area_x_min, sample_area_y_min),
                (sample_area_x_max - 1, sample_area_y_min),
                (sample_area_x_min, sample_area_y_max - 1),
                (sample_area_x_max - 1, sample_area_y_max - 1),
            ]
            for px, py in corners:
                if 0 <= px < img_rgb.width and 0 <= py < img_rgb.height:
                    sample_points.append((px, py))
        
        bg_colors = []
        for px, py in sample_points:
            try:
                pixel = img_rgb.getpixel((px, py))
                bg_colors.append(pixel)
            except Exception:
                continue
        
        if bg_colors:
            # Use median instead of average to avoid outliers (e.g., text pixels)
            sorted_r = sorted([c[0] for c in bg_colors])
            sorted_g = sorted([c[1] for c in bg_colors])
            sorted_b = sorted([c[2] for c in bg_colors])
            mid = len(sorted_r) // 2
            median_r = sorted_r[mid] if len(sorted_r) > 0 else 128
            median_g = sorted_g[mid] if len(sorted_g) > 0 else 128
            median_b = sorted_b[mid] if len(sorted_b) > 0 else 128
            
            # Use relative luminance for better brightness calculation
            # Formula: 0.299*R + 0.587*G + 0.114*B (perceptual brightness)
            brightness = 0.299 * median_r + 0.587 * median_g + 0.114 * median_b
            
            # Use a more conservative threshold (140 instead of 128) to ensure good contrast
            # Also check if the background is very colorful (high saturation) - use white/black for those
            max_component = max(median_r, median_g, median_b)
            min_component = min(median_r, median_g, median_b)
            saturation = (max_component - min_component) / max(max_component, 1) if max_component > 0 else 0
            
            # For highly saturated colors or very light/dark backgrounds, use standard colors
            if brightness > 140 or (brightness > 100 and saturation > 0.3):
                # Light or colorful background: use semi-transparent white with black text
                bg_color = (255, 255, 255, 240)  # More opaque for better readability
                text_color = (0, 0, 0)
            elif brightness < 100:
                # Dark background: use semi-transparent black with white text
                bg_color = (0, 0, 0, 240)  # More opaque for better readability
                text_color = (255, 255, 255)
            else:
                # Medium brightness: default to white background for safety
                bg_color = (255, 255, 255, 240)
                text_color = (0, 0, 0)
        else:
            # Fallback: use high-contrast white background with black text
            bg_color = (255, 255, 255, 240)
            text_color = (0, 0, 0)
        
        text_area = [
            (x_min, y_min),
            (x_max, y_max)
        ]
        draw.rectangle(text_area, fill=bg_color)
        
        # Draw text with outline for better readability
        text_y = y_min + padding
        for line in text_lines:
            text_x = x_min + padding
            
            # Draw text outline/stroke for better contrast
            # This ensures text is readable even if background color detection fails
            outline_color = (255, 255, 255) if text_color == (0, 0, 0) else (0, 0, 0)
            outline_width = 2  # Fixed width for consistent outline
            
            # Draw outline by drawing text with slight offsets in all directions
            for dx in [-outline_width, 0, outline_width]:
                for dy in [-outline_width, 0, outline_width]:
                    if dx != 0 or dy != 0:
                        try:
                            draw.text((text_x + dx, text_y + dy), line, font=font, fill=outline_color)
                        except Exception:
                            pass
            
            # Draw main text on top
            draw.text((text_x, text_y), line, font=font, fill=text_color)
            text_y += measure_text(line, font)[1] + line_spacing
    
    buffer = io.BytesIO()
    annotated.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

app = Flask(__name__)
# Configure CORS to allow all origins (for mobile app development)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "max_age": 3600
    }
})

# Add request logging middleware
@app.before_request
def log_request_info():
    try:
        logger.info(f"Request: {request.method} {request.path}")
        logger.info(f"Remote address: {request.remote_addr}")
    except Exception as e:
        logger.error(f"Error in request logging: {e}")

@app.route("/api/health", methods=["GET", "POST"])
def health():
    return jsonify({"status": "ok", "message": "Server is running"}), 200

def detect_text_regions(img_cv):
    """Detect text regions using contour detection"""
    try:
        # Use morphological operations to find text regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
        morph = cv2.morphologyEx(img_cv, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # Get bounding boxes
        boxes = [cv2.boundingRect(c) for c in contours]
        boxes = [b for b in boxes if b[2] * b[3] > 100]  # Filter small regions
        
        if not boxes:
            return None
        
        # Get combined bounding box
        x = min(b[0] for b in boxes)
        y = min(b[1] for b in boxes)
        w = max(b[0] + b[2] for b in boxes) - x
        h = max(b[1] + b[3] for b in boxes) - y
        
        # Add padding
        padding = 10
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(img_cv.shape[1] - x, w + 2 * padding)
        h = min(img_cv.shape[0] - y, h + 2 * padding)
        
        return (x, y, w, h)
    except Exception as e:
        logger.warning(f"Text region detection failed: {e}")
        return None

def enlarge_textbox_with_opencv(img_cv, bbox, padding_ratio=0.2, min_padding=15, upscale_factor=2.0):
    """
    Use OpenCV to crop around the detected text box, add padding, and upscale
    the region so downstream OCR receives a larger, easier-to-read patch.
    """
    try:
        x, y, w, h = bbox
        pad_w = max(int(w * padding_ratio), min_padding)
        pad_h = max(int(h * padding_ratio), min_padding)
        
        x1 = max(0, x - pad_w)
        y1 = max(0, y - pad_h)
        x2 = min(img_cv.shape[1], x + w + pad_w)
        y2 = min(img_cv.shape[0], y + h + pad_h)
        
        if x2 <= x1 or y2 <= y1:
            logger.info("Invalid textbox bounds after padding; skipping enlargement")
            return img_cv
        
        cropped = img_cv[y1:y2, x1:x2]
        if cropped.size == 0:
            logger.info("Empty crop returned while enlarging textbox; skipping enlargement")
            return img_cv
        
        enlarged = cv2.resize(
            cropped,
            None,
            fx=upscale_factor,
            fy=upscale_factor,
            interpolation=cv2.INTER_CUBIC
        )
        
        logger.info(
            f"Enlarged textbox via OpenCV: "
            f"original {w}x{h} -> cropped {(x2 - x1)}x{(y2 - y1)} "
            f"-> final {enlarged.shape[1]}x{enlarged.shape[0]}"
        )
        return enlarged
    except Exception as e:
        logger.warning(f"Textbox enlargement failed: {e}")
        return img_cv

def deskew_image(img_cv):
    """Deskew image by detecting rotation angle"""
    try:
        # Convert to binary
        _, binary = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find all non-zero points
        coords = np.column_stack(np.where(binary > 0))
        
        if len(coords) < 10:
            return img_cv
        
        # Get minimum area rectangle
        angle = cv2.minAreaRect(coords)[-1]
        
        # Correct angle
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Only correct if angle is significant
        if abs(angle) < 0.5:
            return img_cv
        
        # Rotate image
        (h, w) = img_cv.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img_cv, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        logger.info(f"Deskewed image by {angle:.2f} degrees")
        return rotated
    except Exception as e:
        logger.warning(f"Deskew failed: {e}")
        return img_cv

def preprocess_image_advanced(img, apply_deskew=True):
    """
    Advanced image preprocessing pipeline:
    1. Convert to RGB if needed
    2. Resize if too large
    3. Convert to grayscale
    4. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    5. Denoise
    6. Adaptive thresholding/binarization
    7. Deskew (optional, only when apply_deskew=True)
    8. Crop to text regions (optional)
    """
    # Convert PIL to OpenCV format
    if isinstance(img, Image.Image):
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    else:
        img_cv = img.copy()
    
    # Convert to RGB if needed (handles RGBA, P, etc.)
    if len(img_cv.shape) == 3 and img_cv.shape[2] == 4:
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGRA2BGR)
    
    # Resize if image is too large (improves speed and sometimes accuracy)
    # Increased to 3000px for better phone camera image quality
    max_width = 3000
    if img_cv.shape[1] > max_width:
        ratio = max_width / img_cv.shape[1]
        new_height = int(img_cv.shape[0] * ratio)
        img_cv = cv2.resize(img_cv, (max_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        logger.info(f"Resized image to: {img_cv.shape[1]}x{img_cv.shape[0]}")
    
    # Convert to grayscale
    if len(img_cv.shape) == 3:
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_cv.copy()
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # Increased clipLimit for better contrast on phone images
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    # Denoise using bilateral filter (preserves edges)
    # Adjusted parameters for better phone image quality
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Apply unsharp masking for better text clarity (especially for phone images)
    gaussian = cv2.GaussianBlur(gray, (0, 0), 2.0)
    gray = cv2.addWeighted(gray, 1.5, gaussian, -0.5, 0)
    
    # Deskew the image if requested
    if apply_deskew:
        gray = deskew_image(gray)
    else:
        logger.info("Skipping deskew step because text was already detected")
    
    # Focus on detected text region and enlarge it for easier OCR
    text_region = detect_text_regions(gray)
    if text_region:
        gray = enlarge_textbox_with_opencv(gray, text_region, padding_ratio=0.25, min_padding=20, upscale_factor=1.5)
    else:
        logger.info("No text region detected; using full frame for OCR")
    
    # Apply adaptive thresholding (binarization)
    # Try multiple methods and use the best one
    adaptive_thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Also try Otsu's thresholding
    _, otsu_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Return both versions - OCR can try both
    return {
        'adaptive': adaptive_thresh,
        'otsu': otsu_thresh,
        'grayscale': gray  # Also keep grayscale for some OCR engines
    }

def apply_simple_post_corrections(text):
    """Heuristic fixes for common OCR mistakes without heavy dependencies."""
    if not text:
        return text
    
    import re
    
    def preserve_case(original, replacement):
        """Return replacement preserving simple casing rules."""
        if not original:
            return replacement
        if original.isupper():
            return replacement.upper()
        if original[0].isupper():
            return replacement.capitalize()
        return replacement
    
    corrections = [
        (re.compile(r'\bWHAT\s+IS\s+I\?', re.IGNORECASE), "what is it?"),
        # Fix common EasyOCR confusion: "TAKE I" -> "TAKE IT"
        (re.compile(r'\bTAKE\s+I\b', re.IGNORECASE), "take it"),
    ]
    
    def repl_factory(pattern, replacement):
        def _repl(match):
            return preserve_case(match.group(0), replacement)
        return _repl
    
    for pattern, replacement in corrections:
        text = pattern.sub(repl_factory(pattern, replacement), text)

    # Generic "Aword" → "A word" using spellchecker
    AWORD_PATTERN = re.compile(r'\b([Aa])([A-Z][a-zA-Z]+)\b')

    def split_aword(match):
        prefix = match.group(1)
        rest = match.group(2)
        rest_l = rest.lower()

        # Only split if 'rest' is a known word
        if rest_l in spellchecker:  # or: spellchecker.correction(rest_l) == rest_l
            return f"{prefix} {rest}"
        return match.group(0)

    text = AWORD_PATTERN.sub(split_aword, text)

    return text


def clean_ocr_text(text):
    """Clean OCR text by removing common artifacts and noise"""
    if not text:
        return ""
    
    # Remove common OCR artifacts
    import re
    # Remove excessive whitespace (but preserve single spaces)
    text = re.sub(r'\s+', ' ', text)
    # Remove trailing/leading special characters that are often OCR errors
    text = re.sub(r'^[<>\|`~]+', '', text)
    text = re.sub(r'[<>\|`~]+$', '', text)
    # Remove single character lines that are likely noise
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Keep lines that are meaningful (more than 1 char, or common single chars like 'a', 'I')
        if len(line) > 1 or line.lower() in ['a', 'i']:
            cleaned_lines.append(line)
    text = ' '.join(cleaned_lines)

    text = normalize_punctuation_by_language(text)
    text = apply_simple_post_corrections(text)
    
    return text.strip()

def invert_image(img):
    """反相影像（黑白顛倒）"""
    if isinstance(img, Image.Image):
        img_np = np.array(img)
    else:
        img_np = img
    if len(img_np.shape) == 2:
        # 灰階
        inverted = 255 - img_np
    else:
        # 彩色
        inverted = 255 - img_np
    if isinstance(img, Image.Image):
        return Image.fromarray(inverted)
    return inverted


def has_dark_background(img, threshold: float = 140.0) -> bool:
    """
    Heuristic: returns True if the image is overall dark (likely white/bright text on dark background).
    Uses average luminance on a grayscale version of the image.
    """
    try:
        if isinstance(img, Image.Image):
            gray = img.convert("L")
            arr = np.array(gray)
        else:
            # Assume OpenCV-style image
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            arr = gray
        mean_brightness = float(arr.mean())
        logger.info(f"Estimated image brightness: {mean_brightness:.1f}")
        return mean_brightness < threshold
    except Exception as e:
        logger.warning(f"Failed to estimate background brightness: {e}")
        return False

def ocr_with_easyocr(img):
    """Perform OCR using EasyOCR (支援原圖與反相圖)"""
    try:
        reader = get_easyocr_reader()
        if reader is None:
            return []
        
        results = []
        
        # 原圖 OCR
        try:
            # EasyOCR works best with original images, not heavily preprocessed ones
            # Convert PIL to numpy array
            if isinstance(img, Image.Image):
                # Ensure RGB mode
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img_array = np.array(img)
            else:
                img_array = img
            
            # Ensure 3-channel RGB
            if len(img_array.shape) == 2:  # Grayscale
                img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
            elif img_array.shape[2] == 4:  # RGBA
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
            
            logger.info("Running EasyOCR on original image (timeout: 15s)...")
            detections = run_with_timeout(
                lambda: reader.readtext(img_array),
                timeout_seconds=15,
                default_return=[]
            )
            
            if detections:
                logger.info(f"EasyOCR detected {len(detections)} text regions")

                # Filter out low-confidence detections
                filtered = [det for det in detections if float(det[2]) >= MIN_CONFIDENCE]

                # Log all detections for debugging
                for i, det in enumerate(detections):
                    confidence = float(det[2])
                    kept = confidence >= MIN_CONFIDENCE
                    logger.info(
                        f"  Detection {i+1}: '{det[1]}' (confidence: {confidence:.3f}) "
                        f"{'(kept)' if kept else '(discarded < MIN_CONFIDENCE)'}"
                    )

                if not filtered:
                    logger.warning(
                        f"All EasyOCR detections on original image were below "
                        f"MIN_CONFIDENCE={MIN_CONFIDENCE}"
                    )

                # Combine only high-confidence text
                segments = []
                for det in filtered:
                    segment_text = clean_ocr_text(det[1])
                    if not segment_text:
                        continue
                    try:
                        bbox_points = [[float(p[0]), float(p[1])] for p in det[0]]
                    except Exception:
                        bbox_points = []
                    segments.append({
                        "text": segment_text,
                        "bbox": bbox_points,
                        "confidence": float(det[2])
                    })
                text_parts = [det[1] for det in filtered]
                text = ' '.join(text_parts).strip()
                text = clean_ocr_text(text)

                if text:
                    avg_confidence = (
                        sum(float(det[2]) for det in filtered) / max(1, len(filtered))
                    )
                    results.append({
                        'text': text,
                        'length': len(text),
                        'config': 'original_easyocr',
                        'engine': 'easyocr',
                        'confidence': avg_confidence,
                        'segments': segments,
                        'coordinate_space': 'original'
                    })
                # Do not return any text if everything is below MIN_CONFIDENCE
            else:
                logger.warning("EasyOCR on original image returned no results or timed out")
        except Exception as e:
            logger.warning(f"EasyOCR failed with original image: {e}")
        
        # 反相圖 OCR - only if background appears dark (likely white/bright text on dark background)
        if has_dark_background(img):
            try:
                img_invert = invert_image(img)
                logger.info("Running EasyOCR on inverted image (timeout: 15s)...")
                img_array = np.array(img_invert)
                if len(img_array.shape) == 2:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
                elif img_array.shape[2] == 4:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
                detections = run_with_timeout(
                    lambda: reader.readtext(img_array),
                    timeout_seconds=15,
                    default_return=[]
                )
                if detections:
                    filtered = [det for det in detections if float(det[2]) >= MIN_CONFIDENCE]
                    segments = []
                    for det in filtered:
                        segment_text = clean_ocr_text(det[1])
                        if not segment_text:
                            continue
                        try:
                            bbox_points = [[float(p[0]), float(p[1])] for p in det[0]]
                        except Exception:
                            bbox_points = []
                        segments.append({
                            "text": segment_text,
                            "bbox": bbox_points,
                            "confidence": float(det[2])
                        })
                    text_parts = [det[1] for det in filtered]
                    text = ' '.join(text_parts).strip()
                    text = clean_ocr_text(text)
                    if text:
                        avg_confidence = (
                            sum(float(det[2]) for det in filtered) / max(1, len(filtered))
                        )
                        results.append({
                            'text': text,
                            'length': len(text),
                            'config': 'inverted_easyocr',
                            'engine': 'easyocr',
                            'confidence': avg_confidence,
                            'segments': segments,
                            'coordinate_space': 'original'  # bounding boxes still align with original image
                        })
            except Exception as e:
                logger.warning(f"EasyOCR failed with inverted image: {e}")
        else:
            logger.info("Skipping inverted EasyOCR pass (background not dark enough for white text)")
        
        release_gpu_memory()  # 執行完釋放 GPU 記憶體
        return results
    except Exception as e:
        logger.error(f"EasyOCR error: {e}")
        return []

def ocr_with_preprocess_easyocr(img, apply_deskew=True, timeout_seconds=15):
    reader = get_easyocr_reader()
    if reader is None:
        return []

    # Preprocess image with your advanced pipeline
    processed = preprocess_image_advanced(img, apply_deskew=apply_deskew)  # returns grayscale, adaptive, otsu

    candidates = []

    for name, proc_img in processed.items():
        # 原始
        try:
            # Convert grayscale/BW back to 3-channel RGB for EasyOCR
            if len(proc_img.shape) == 2:
                proc_rgb = cv2.cvtColor(proc_img, cv2.COLOR_GRAY2RGB)
            else:
                proc_rgb = proc_img

            if name == "grayscale":
                # Speed up grayscale pass by downscaling overly large frames before OCR
                h, w = proc_rgb.shape[:2]
                max_dim = max(h, w)
                target_max = 1500
                if max_dim > target_max:
                    scale = target_max / max_dim
                    new_size = (int(w * scale), int(h * scale))
                    proc_rgb = cv2.resize(proc_rgb, new_size, interpolation=cv2.INTER_AREA)
                    logger.info(
                        f"Downscaled grayscale image for faster OCR: {w}x{h} -> {new_size[0]}x{new_size[1]}"
                    )

            logger.info(f"Running EasyOCR on preprocessed {name} (timeout: {timeout_seconds}s)...")
            detections = run_with_timeout(
                lambda: reader.readtext(proc_rgb),
                timeout_seconds=timeout_seconds,
                default_return=[]
            )

            if detections:
                # Filter out low-confidence detections
                filtered = [d for d in detections if float(d[2]) >= MIN_CONFIDENCE]

                # Log all detections for debugging
                for i, d in enumerate(detections):
                    confidence = float(d[2])
                    kept = confidence >= MIN_CONFIDENCE
                    logger.info(
                        f"  [{name}] Detection {i+1}: '{d[1]}' (confidence: {confidence:.3f}) "
                        f"{'(kept)' if kept else '(discarded < MIN_CONFIDENCE)'}"
                    )

                if not filtered:
                    logger.warning(
                        f"[{name}] All EasyOCR detections were below MIN_CONFIDENCE={MIN_CONFIDENCE}"
                    )

                # Use only high-confidence detections
                segments = []
                for d in filtered:
                    segment_text = clean_ocr_text(d[1])
                    if not segment_text:
                        continue
                    try:
                        bbox_points = [[float(p[0]), float(p[1])] for p in d[0]]
                    except Exception:
                        bbox_points = []
                    segments.append({
                        "text": segment_text,
                        "bbox": bbox_points,
                        "confidence": float(d[2])
                    })
                text_parts = [d[1] for d in filtered]
                text = " ".join(text_parts).strip()
                text = clean_ocr_text(text)

                if text and filtered:
                    avg_conf = (
                        sum(float(d[2]) for d in filtered)
                        / max(1, len(filtered))
                    )
                    candidates.append({
                        "text": text,
                        "engine": "easyocr",
                        "config": f"preprocess_{name}",
                        "confidence": avg_conf,
                        "length": len(text),
                        "segments": segments,
                        "coordinate_space": f"preprocess_{name}"
                    })
                # Do not return any text if everything is below MIN_CONFIDENCE

                logger.info(f"[{name}] detections: {len(detections)}")
            else:
                logger.warning(f"[{name}] returned no results or timed out")

        except Exception as e:
            logger.warning(f"EasyOCR failed on {name}: {e}")

        # 只對 grayscale 做反相 OCR
        if name == 'grayscale':
            try:
                proc_invert = invert_image(proc_img)
                if len(proc_invert.shape) == 2:
                    proc_rgb = cv2.cvtColor(proc_invert, cv2.COLOR_GRAY2RGB)
                else:
                    proc_rgb = proc_invert
                logger.info(f"Running EasyOCR on inverted preprocessed {name} (timeout: {timeout_seconds}s)...")
                detections = run_with_timeout(
                    lambda: reader.readtext(proc_rgb),
                    timeout_seconds=timeout_seconds,
                    default_return=[]
                )
                if detections:
                    filtered = [d for d in detections if float(d[2]) >= MIN_CONFIDENCE]
                    segments = []
                    for d in filtered:
                        segment_text = clean_ocr_text(d[1])
                        if not segment_text:
                            continue
                        try:
                            bbox_points = [[float(p[0]), float(p[1])] for p in d[0]]
                        except Exception:
                            bbox_points = []
                        segments.append({
                            "text": segment_text,
                            "bbox": bbox_points,
                            "confidence": float(d[2])
                        })
                    text_parts = [d[1] for d in filtered]
                    text = " ".join(text_parts).strip()
                    text = clean_ocr_text(text)
                    if text and filtered:
                        avg_conf = (
                            sum(float(d[2]) for d in filtered)
                            / max(1, len(filtered))
                        )
                        candidates.append({
                            "text": text,
                            "engine": "easyocr",
                            "config": f"inverted_preprocess_{name}",
                            "confidence": avg_conf,
                            "length": len(text),
                            "segments": segments,
                            "coordinate_space": f"inverted_preprocess_{name}"
                        })
            except Exception as e:
                logger.warning(f"EasyOCR failed on inverted {name}: {e}")

    release_gpu_memory()  # 執行完釋放 GPU 記憶體
    return candidates

@app.route("/api/test", methods=["GET", "POST", "OPTIONS"])
def test():
    """Simple test endpoint to verify connectivity"""
    logger.info(f"Test endpoint called from {request.remote_addr}")
    
    # Pre-initialize EasyOCR on first test call to avoid timeout on first OCR request
    try:
        get_easyocr_reader()
    except Exception as e:
        logger.warning(f"Could not pre-initialize EasyOCR: {e}")
    
    # Get server IP address dynamically
    import socket
    try:
        # Get the IP address of the network interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        server_ip = s.getsockname()[0]
        s.close()
    except Exception:
        # Fallback to localhost if can't determine IP
        server_ip = "127.0.0.1"
    
    return jsonify({
        "status": "ok", 
        "message": "Connection successful", 
        "ip": request.remote_addr,
        "server_ip": server_ip,
        "port": 5003,
        "easyocr_ready": easyocr_reader is not None
    }), 200

@app.route("/api/translate", methods=["POST", "OPTIONS"])
def api_translate():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    try:
        data = request.get_json()
        text = data.get("text", "")
        target_lang = data.get("target_lang", "ZH")
        if not text:
            return jsonify({"error": "No text provided"}), 400
        translated = translate_text_with_deepl(text, target_lang)
        if translated:
            return jsonify({"translated": translated})
        else:
            return jsonify({"error": "Translation failed"}), 500
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/ocr", methods=["POST", "OPTIONS"])
def ocr():
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        logger.info("CORS preflight request received")
        return jsonify({"status": "ok"}), 200
    
    try:
        logger.info(f"Received OCR request from {request.remote_addr}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Content-Length: {request.content_length}")
        
        # Get the base64 image from request
        data = request.get_json()
        if not data:
            logger.warning("No JSON data in request body")
            return jsonify({"error": "No JSON data provided"}), 400
        if "image" not in data:
            logger.warning("No image field in request data")
            logger.info(f"Request data keys: {list(data.keys()) if data else 'None'}")
            return jsonify({"error": "No image provided"}), 400
        
        logger.info(f"Image data length: {len(data.get('image', ''))}")
        logger.info(f"Target language: {data.get('target_lang', 'Not specified')}")
        logger.info(f"Return overlay: {data.get('return_overlay', False)}")
        
        target_lang = data.get("target_lang")
        return_overlay = bool(data.get("return_overlay", False))
        include_segment_data = bool(data.get("include_segment_data", False))
        overlay_boxes_only = bool(data.get("overlay_boxes_only", False))
        if return_overlay and not target_lang and not overlay_boxes_only:
            target_lang = "ZH"
            logger.info("return_overlay requested without target_lang; defaulting to 'ZH'")
        
        base64_str = data["image"]
        logger.info(f"Image data length: {len(base64_str)}")
        
        # Remove data URL prefix if present
        if base64_str.startswith("data:image"):
            base64_str = base64_str.split(",")[1]
        
        # Decode base64 to image
        logger.info("Decoding base64 image...")
        img_bytes = base64.b64decode(base64_str)
        img = Image.open(io.BytesIO(img_bytes))
        
        # Fix EXIF orientation (critical for phone images)
        try:
            img = ImageOps.exif_transpose(img)
            logger.info("Applied EXIF orientation correction")
        except Exception as e:
            logger.warning(f"Could not apply EXIF orientation: {e}")
        
        logger.info(f"Image opened: {img.size}, mode: {img.mode}")
        
        all_results = []
        best_candidate = None

        # Original EasyOCR passes (with 15s timeout per pass)
        logger.info("Starting original EasyOCR passes...")
        easyocr_original = ocr_with_easyocr(img)
        logger.info(f"Original EasyOCR completed: {len(easyocr_original)} results")
        all_results.extend(easyocr_original)

        if easyocr_original:
            original_best = max(easyocr_original, key=lambda r: r.get("confidence", 0))
            if original_best.get("confidence", 0) >= HIGH_CONFIDENCE_THRESHOLD:
                logger.info(
                    "High-confidence original OCR result detected "
                    f"({original_best['confidence']:.3f} >= {HIGH_CONFIDENCE_THRESHOLD}); "
                    "skipping preprocessing passes."
                )
                best_candidate = original_best

        easyocr_preprocessed = []
        if best_candidate is None:
            apply_deskew = len(easyocr_original) == 0
            if apply_deskew:
                logger.info("No text from original OCR; enabling deskew for preprocessing and increasing timeout to 30s")
                preprocess_timeout = 30
            else:
                logger.info("Text detected in original OCR; skipping deskew during preprocessing")
                preprocess_timeout = 15

            # Preprocessed EasyOCR passes (OpenCV enhanced, with adjustable timeout per pass)
            logger.info("Starting preprocessed EasyOCR passes...")
            easyocr_preprocessed = ocr_with_preprocess_easyocr(img, apply_deskew=apply_deskew, timeout_seconds=preprocess_timeout)
            logger.info(f"Preprocessed EasyOCR completed: {len(easyocr_preprocessed)} results")
            all_results.extend(easyocr_preprocessed)

        logger.info(f"Total results collected: {len(all_results)}")

        if not all_results:
            return jsonify({"text": "No text detected"})

        if best_candidate is None:
            # Build word frequency map across all candidates
            word_freq = {}
            for r in all_results:
                text = r.get("text", "") or ""
                for w in text.split():
                    key = w.lower()
                    word_freq[key] = word_freq.get(key, 0) + 1

            # Sort by confidence + text length + config priority + word frequency consistency
            def score(r):
                base = r["confidence"] * 100
                base += r["length"]
                base += get_config_priority(r.get("config", "")) * CONFIG_PRIORITY_WEIGHT

                text = r.get("text", "") or ""
                words = [w.lower() for w in text.split() if w.strip()]
                if words:
                    # Average how often this candidate's words appear across all configs
                    avg_freq = sum(word_freq.get(w, 1) for w in set(words)) / max(1, len(set(words)))
                    base += avg_freq * WORD_FREQUENCY_WEIGHT

                return base

            all_results.sort(key=score, reverse=True)
            best_candidate = all_results[0]

        logger.info(f"Selected best OCR: {best_candidate['config']} conf={best_candidate['confidence']:.3f}")

        response_payload = {
            "text": best_candidate['text'],
            "confidence": best_candidate['confidence'],
            "engine": best_candidate['engine'],
            "mode": best_candidate['config']
        }

        if include_segment_data and best_candidate.get("segments"):
            response_payload["segments"] = best_candidate["segments"]

        translated_text = None
        if target_lang:
            translated_text = translate_text_with_deepl(best_candidate['text'], target_lang)
            if translated_text:
                response_payload["translated_text"] = translated_text
                response_payload["target_lang"] = target_lang

        if return_overlay:
            overlay_segments = None
            if best_candidate.get("coordinate_space") == "original":
                overlay_segments = best_candidate.get("segments")
            if not overlay_segments and easyocr_original:
                # Fallback to best original segments if current result came from preprocessing
                sorted_original = sorted(
                    easyocr_original,
                    key=lambda r: r.get("confidence", 0),
                    reverse=True
                )
                for candidate in sorted_original:
                    if candidate.get("segments"):
                        overlay_segments = candidate["segments"]
                        break
            overlay_payload = None
            if overlay_boxes_only:
                overlay_payload = merge_segments_into_lines(overlay_segments) if overlay_segments else []
            elif target_lang:
                overlay_payload = translate_segment_lines(overlay_segments, target_lang) if overlay_segments else []
            if overlay_payload:
                overlay_base64 = render_translated_overlay(
                    img,
                    overlay_payload,
                    boxes_only=overlay_boxes_only or not target_lang
                )
            else:
                overlay_base64 = None
            if overlay_base64:
                response_payload["annotated_image"] = f"data:image/png;base64,{overlay_base64}"
                if include_segment_data and overlay_payload:
                    response_payload["segments"] = overlay_payload

        return jsonify(response_payload)
    
    except Exception as e:
        logger.error(f"Error processing OCR: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Starting Flask server on 0.0.0.0:5003 (accessible from network)")
    # Pre-initialize EasyOCR in background to avoid first-request timeout
    logger.info("Pre-initializing EasyOCR (this may take a moment)...")
    try:
        get_easyocr_reader()
        logger.info("EasyOCR pre-initialized successfully")
    except Exception as e:
        logger.warning(f"Could not pre-initialize EasyOCR: {e}. Will initialize on first use.")
    
    app.run(host="0.0.0.0", port=5003, threaded=True, debug=False)
