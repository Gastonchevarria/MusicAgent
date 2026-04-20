import os
import random
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --- Arcadia Music color palette (dark electronic / cyberpunk) ---

ARCADIA_MOODS = {
    # Dark & Aggressive (Industrial, Peak Time, Cyberpunk)
    "dark":        {"primary": (3, 3, 12),    "secondary": (20, 5, 40),   "accent": (180, 0, 255)},
    "aggressive":  {"primary": (5, 2, 10),    "secondary": (40, 5, 15),   "accent": (255, 0, 80)},
    "intense":     {"primary": (5, 2, 10),    "secondary": (40, 5, 15),   "accent": (255, 0, 80)},
    "dystopian":   {"primary": (3, 3, 8),     "secondary": (15, 15, 30),  "accent": (0, 255, 140)},
    "mechanical":  {"primary": (3, 3, 8),     "secondary": (15, 15, 30),  "accent": (0, 255, 140)},
    # Hypnotic & Deep (Melodic Techno, Deep Techno)
    "hypnotic":    {"primary": (5, 5, 18),    "secondary": (15, 8, 40),   "accent": (0, 180, 255)},
    "mesmerizing": {"primary": (5, 5, 18),    "secondary": (15, 8, 40),   "accent": (0, 180, 255)},
    "deep":        {"primary": (5, 5, 18),    "secondary": (15, 8, 40),   "accent": (0, 180, 255)},
    "introspective":{"primary": (5, 5, 18),   "secondary": (15, 8, 40),   "accent": (0, 180, 255)},
    # Emotional & Euphoric (Progressive, Melodic House, Trance)
    "emotional":   {"primary": (8, 5, 22),    "secondary": (25, 10, 50),  "accent": (140, 80, 255)},
    "euphoric":    {"primary": (8, 5, 22),    "secondary": (25, 10, 50),  "accent": (140, 80, 255)},
    "uplifting":   {"primary": (8, 5, 22),    "secondary": (25, 10, 50),  "accent": (140, 80, 255)},
    "cinematic":   {"primary": (8, 5, 22),    "secondary": (25, 10, 50),  "accent": (140, 80, 255)},
    "dreamy":      {"primary": (8, 5, 22),    "secondary": (25, 10, 50),  "accent": (140, 80, 255)},
    # Futuristic & Neon (Cyberpunk, Acid)
    "futuristic":  {"primary": (3, 3, 12),    "secondary": (10, 20, 35),  "accent": (0, 255, 200)},
    "psychedelic": {"primary": (8, 3, 15),    "secondary": (25, 10, 40),  "accent": (255, 100, 0)},
    "quirky":      {"primary": (5, 5, 15),    "secondary": (20, 10, 35),  "accent": (0, 255, 180)},
    # Warm & Organic (Organic House)
    "warm":        {"primary": (10, 8, 5),    "secondary": (30, 18, 8),   "accent": (255, 160, 40)},
    "groovy":      {"primary": (10, 8, 5),    "secondary": (30, 18, 8),   "accent": (255, 160, 40)},
    "sensual":     {"primary": (10, 8, 5),    "secondary": (30, 18, 8),   "accent": (255, 160, 40)},
    # Powerful & Explosive (Peak Time)
    "powerful":    {"primary": (5, 2, 10),    "secondary": (30, 5, 20),   "accent": (255, 0, 120)},
    "relentless":  {"primary": (5, 2, 10),    "secondary": (30, 5, 20),   "accent": (255, 0, 120)},
    "explosive":   {"primary": (5, 2, 10),    "secondary": (30, 5, 20),   "accent": (255, 0, 120)},
}


def get_arcadia_colors(mood: str) -> dict:
    """Get Arcadia color palette for a mood. Always returns cosmic tones."""
    mood_lower = mood.lower()
    for key, colors in ARCADIA_MOODS.items():
        if key in mood_lower:
            return colors
    return {"primary": (5, 5, 18), "secondary": (15, 8, 40), "accent": (0, 180, 255)}


def _get_font(size: int):
    """Load DejaVuSans-Bold at given size. Works on Ubuntu VPS and macOS."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/local/share/fonts/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap_text(text: str, font, max_width: int) -> list:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_text(text: str, max_width: int, max_height: int) -> tuple:
    """Find largest font size that fits text in bounds (max 3 lines).
    Returns (font, lines)."""
    for size in range(60, 24, -2):
        font = _get_font(size)
        lines = _wrap_text(text, font, max_width)
        if len(lines) > 3:
            continue
        line_height = font.getbbox("Ay")[3] + 8
        total_height = line_height * len(lines)
        if total_height <= max_height:
            return font, lines
    font = _get_font(26)
    lines = _wrap_text(text, font, max_width)
    return font, lines[:3]


def _draw_radial_gradient(img, center_color: tuple, edge_color: tuple):
    """Draw radial gradient using concentric ellipses + blur."""
    width, height = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, height], fill=edge_color)

    steps = 80
    for i in range(steps):
        ratio = i / steps
        mx = int(width * 0.45 * (1 - ratio))
        my = int(height * 0.45 * (1 - ratio))
        r = int(edge_color[0] + (center_color[0] - edge_color[0]) * ratio)
        g = int(edge_color[1] + (center_color[1] - edge_color[1]) * ratio)
        b = int(edge_color[2] + (center_color[2] - edge_color[2]) * ratio)
        draw.ellipse([mx, my, width - mx, height - my], fill=(r, g, b))

    # Smooth the banding
    blurred = img.filter(ImageFilter.GaussianBlur(radius=20))
    img.paste(blurred)


def _draw_stars(img, count: int = 120):
    """Draw random star particles for cosmic effect."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = img.size
    for _ in range(count):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        size = random.randint(1, 3)
        alpha = random.randint(60, 200)
        draw.ellipse([x, y, x + size, y + size], fill=(255, 255, 255, alpha))

    # Convert base to RGBA, composite, convert back
    base_rgba = img.convert("RGBA")
    composite = Image.alpha_composite(base_rgba, overlay)
    img.paste(composite.convert("RGB"))


def _draw_glow_border(img, accent: tuple, width_px: int = 3):
    """Draw a subtle glowing border inside the image."""
    glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow_layer)
    w, h = img.size
    margin = 20
    for i in range(width_px):
        alpha = 80 - i * 20
        if alpha <= 0:
            break
        color = (*accent, alpha)
        draw.rectangle(
            [margin + i, margin + i, w - margin - i, h - margin - i],
            outline=color,
        )

    base_rgba = img.convert("RGBA")
    composite = Image.alpha_composite(base_rgba, glow_layer)
    img.paste(composite.convert("RGB"))


def create_thumbnail(title: str, mood: str, output_path: str):
    """
    Generate 1280x720 Arcadia Music branded thumbnail.

    - Radial gradient background in dark electronic tones
    - Star particle overlay
    - Auto-sized, word-wrapped title with text shadow
    - "Arcadia Music" branding at bottom
    - Subtle neon glow border
    """
    width, height = 1280, 720
    colors = get_arcadia_colors(mood)
    primary = colors["primary"]
    secondary = colors["secondary"]
    accent = colors["accent"]

    # Lighter center for radial gradient
    center = tuple(min(c + 30, 255) for c in primary)

    img = Image.new("RGB", (width, height))

    # 1. Radial gradient background
    _draw_radial_gradient(img, center, secondary)

    # 2. Star particles
    _draw_stars(img, count=120)

    # 3. Glow border
    _draw_glow_border(img, accent)

    draw = ImageDraw.Draw(img)

    # 4. Title -- auto-sized, word-wrapped, centered in 70% zone
    text_max_w = int(width * 0.70)
    text_max_h = int(height * 0.45)
    font, lines = _fit_text(title, text_max_w, text_max_h)
    line_height = font.getbbox("Ay")[3] + 8
    total_text_h = line_height * len(lines)
    start_y = (height // 2) - (total_text_h // 2) - 20

    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        line_w = bbox[2]
        x = (width - line_w) // 2
        y = start_y + i * line_height
        # Text shadow
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0))
        draw.text((x + 1, y + 1), line, font=font, fill=(0, 0, 0))
        # Main text
        draw.text((x, y), line, font=font, fill="white")

    # 5. Branding -- bottom center
    brand_font = _get_font(22)
    brand_text = "Arcadia Music"
    brand_bbox = brand_font.getbbox(brand_text)
    brand_x = (width - brand_bbox[2]) // 2
    brand_y = height - 55
    brand_color = tuple(min(c + 100, 255) for c in accent)
    draw.text((brand_x, brand_y), brand_text, font=brand_font, fill=brand_color)

    # Save
    dirname = os.path.dirname(output_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)


# --- Video creation (updated in Task 5) ---

def create_video_with_visualizer(mp3_path: str, thumb_path: str, output_path: str):
    """
    Create 1280x720 video with spectrum analyzer and Arcadia Music branding.
    - Thumbnail background with showfreqs spectrum bars (neon cyan/purple)
    - 'Arcadia Music' drawtext watermark
    """
    dirname = os.path.dirname(output_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Helvetica.ttc"

    # Try showfreqs first (spectrum bars), fall back to showwaves if unavailable
    filter_complex = (
        "[1:a]aformat=channel_layouts=stereo[a_stereo];"
        "[a_stereo]showfreqs=mode=bar:s=1280x180:fscale=log:"
        "ascale=log:colors=0x00ccff|0x8800ff:win_size=2048[freq];"
        "[0:v][freq]overlay=0:540[with_freq];"
        f"[with_freq]drawtext=text='Arcadia Music':"
        f"fontfile={font_path}:fontsize=22:"
        f"fontcolor=white@0.35:x=w-tw-20:y=h-th-15[outv]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", thumb_path,
        "-i", mp3_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "1:a",
        "-c:v", "libx264", "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Fallback: use showwaves if showfreqs not available
        filter_complex_fallback = (
            "[1:a]aformat=channel_layouts=stereo[a_stereo];"
            "[a_stereo]showwaves=s=1280x180:mode=cline:"
            "colors=0x00ccff@0.7:rate=30[waves];"
            "[0:v][waves]overlay=0:540[with_waves];"
            f"[with_waves]drawtext=text='Arcadia Music':"
            f"fontfile={font_path}:fontsize=22:"
            f"fontcolor=white@0.35:x=w-tw-20:y=h-th-15[outv]"
        )
        cmd_fallback = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", thumb_path,
            "-i", mp3_path,
            "-filter_complex", filter_complex_fallback,
            "-map", "[outv]", "-map", "1:a",
            "-c:v", "libx264", "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path,
        ]
        subprocess.run(cmd_fallback, check=True)


def create_youtube_short(audio_path: str, thumbnail_path: str, output_path: str):
    """
    Generate vertical 1080x1920 YouTube Short.
    - Thumbnail in upper half, spectrum visualizer in lower half
    - Arcadia Music branding at bottom
    - Max 59 seconds
    """
    dirname = os.path.dirname(output_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Helvetica.ttc"

    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x050510[bg];"
        "[1:a]aformat=channel_layouts=stereo[a_stereo];"
        "[a_stereo]showfreqs=mode=bar:s=1080x400:fscale=log:"
        "ascale=log:colors=0x00ccff|0x8800ff:win_size=2048[freq];"
        "[bg][freq]overlay=0:1200[with_freq];"
        f"[with_freq]drawtext=text='Arcadia Music':"
        f"fontfile={font_path}:fontsize=28:"
        f"fontcolor=white@0.4:x=(w-tw)/2:y=h-60[outv]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", thumbnail_path,
        "-i", audio_path,
        "-t", "59",
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "1:a",
        "-c:v", "libx264", "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Fallback with showwaves
        filter_fallback = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x050510[bg];"
            "[1:a]aformat=channel_layouts=stereo[a_stereo];"
            "[a_stereo]showwaves=s=1080x400:mode=cline:"
            "colors=0x00ccff@0.7:rate=30[waves];"
            "[bg][waves]overlay=0:1200[with_waves];"
            f"[with_waves]drawtext=text='Arcadia Music':"
            f"fontfile={font_path}:fontsize=28:"
            f"fontcolor=white@0.4:x=(w-tw)/2:y=h-60[outv]"
        )
        cmd_fallback = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", thumbnail_path,
            "-i", audio_path,
            "-t", "59",
            "-filter_complex", filter_fallback,
            "-map", "[outv]", "-map", "1:a",
            "-c:v", "libx264", "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path,
        ]
        subprocess.run(cmd_fallback, check=True)
