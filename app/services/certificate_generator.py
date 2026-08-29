# -*- coding: utf-8 -*-
"""
ASILBEK MATH — Diplom/Sertifikat generatori
Render (Linux) va local Windows uchun universal.

Ishlatilishi (aiogram handler ichida):
    from app.services.certificate_generator import generate_certificate
    from aiogram.types import FSInputFile

    path = generate_certificate(
        full_name="Abdurahmonov Muhammadali Jamoliddin o'g'li",
        percent=95,
        correct=38,
        total=40,
        cert_id="AM-2026-0842",
        date_str="27.08.2026",
    )
    await message.answer_photo(FSInputFile(path), caption="Tabriklaymiz! 🎉")
"""

import io
import math
import os
import uuid
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ----------------------------------------------------------------------
# RANGLAR
# ----------------------------------------------------------------------
W, H = 1920, 1280

NAVY       = (16, 26, 51)
NAVY_LIGHT = (26, 40, 74)
CREAM      = (250, 247, 238)
GOLD       = (196, 155, 74)
GOLD_LIGHT = (222, 190, 122)
TEXT_DARK  = (17, 24, 45)
TEXT_GOLD  = (176, 130, 45)
WHITE      = (255, 255, 255)


# ----------------------------------------------------------------------
# FONTLAR — Render (Linux) va Windows uchun fallback
# ----------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent

def _find_font(*names) -> str:
    """Berilgan nomlar bo'yicha mavjud fontni topadi."""
    search_dirs = [
        _SCRIPT_DIR / "fonts",              # app/services/fonts/
        _SCRIPT_DIR.parent / "fonts",       # app/fonts/
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation"),
        Path("/usr/share/fonts"),
        Path("C:/Windows/Fonts"),
    ]
    for name in names:
        for d in search_dirs:
            p = Path(d) / name
            if p.exists():
                return str(p)
    return ""

F_SERIF_BOLD = _find_font("DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf", "georgiab.ttf", "Georgia Bold.ttf")
F_SERIF      = _find_font("DejaVuSerif.ttf",      "LiberationSerif-Regular.ttf", "georgia.ttf", "Georgia.ttf")
F_SANS_BOLD  = _find_font("DejaVuSans-Bold.ttf",  "LiberationSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf")
F_SANS       = _find_font("DejaVuSans.ttf",        "LiberationSans-Regular.ttf", "arial.ttf", "Arial.ttf")
F_SCRIPT     = _find_font("DancingScript.ttf", "DejaVuSerif-Italic.ttf", "LiberationSerif-Italic.ttf")


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    if path and Path(path).exists():
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _text_w(draw, txt, f):
    bbox = draw.textbbox((0, 0), txt, font=f)
    return bbox[2] - bbox[0]


def _center_text(draw, cx, y, txt, f, fill, tracking=0):
    if tracking == 0:
        w = _text_w(draw, txt, f)
        draw.text((cx - w / 2, y), txt, font=f, fill=fill)
        return
    widths = [_text_w(draw, ch, f) + tracking for ch in txt]
    total = sum(widths) - tracking
    x = cx - total / 2
    for ch, w in zip(txt, widths):
        draw.text((x, y), ch, font=f, fill=fill)
        x += w


def _draw_diamond_logo(draw, cx, cy, r):
    GOLD_DARK = (168, 128, 56)
    pts_outer = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    draw.polygon(pts_outer, fill=GOLD)
    draw.polygon([(cx, cy - r), (cx - r, cy), (cx, cy + r)], fill=GOLD_LIGHT)
    b = r * 0.24
    pts_inner = [(cx, cy - r + b), (cx + r - b, cy), (cx, cy + r - b), (cx - r + b, cy)]
    draw.polygon(pts_inner, fill=CREAM)
    rw, rh = r * 0.62, r * 0.6
    peak = [
        (cx, cy - rh * 0.5),
        (cx + rw * 0.6, cy + rh * 0.48),
        (cx + rw * 0.28, cy + rh * 0.48),
        (cx, cy - rh * 0.02),
        (cx - rw * 0.28, cy + rh * 0.48),
        (cx - rw * 0.6, cy + rh * 0.48),
    ]
    draw.polygon(peak, fill=GOLD)
    draw.polygon(
        [(cx, cy - rh * 0.5), (cx + rw * 0.28, cy + rh * 0.48), (cx, cy - rh * 0.02)],
        fill=GOLD_DARK,
    )


def _make_leaf_img(length, width, color):
    length, width = max(2, int(length)), max(2, int(width))
    im = Image.new("RGBA", (length, width), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([0, 0, length - 1, width - 1], fill=color)
    return im


def _paste_leaf(base_rgba, cx, cy, angle_deg, length, width, color):
    leaf = _make_leaf_img(length, width, color)
    leaf = leaf.rotate(-angle_deg, expand=True, resample=Image.BICUBIC)
    lw, lh = leaf.size
    base_rgba.alpha_composite(leaf, (int(cx - lw / 2), int(cy - lh / 2)))


def _draw_laurel_wreath(base_rgba, cx, cy, n=7, maxR=48, height=78):
    leaf_col = GOLD + (255,)
    alt_col  = GOLD_LIGHT + (255,)
    for side in (-1, 1):
        for i in range(n):
            t = i / (n - 1)
            sweep = t * 95
            px = cx + side * maxR * math.sin(math.radians(sweep))
            py = cy - t * height
            outward_angle = side * (28 + t * 42)
            size = 17 * (0.5 + 0.5 * t)
            wid  = 6.5 * (0.55 + 0.45 * t)
            col  = leaf_col if i % 2 == 0 else alt_col
            _paste_leaf(base_rgba, px, py, outward_angle, size, wid, col)


def _corner_ornament(draw, x, y, flip_x=False, flip_y=False):
    sx = -1 if flip_x else 1
    sy = -1 if flip_y else 1
    lines = [
        (0, 30, 60, 30), (60, 30, 60, 0),
        (0, 55, 85, 55), (85, 55, 85, 0),
        (20, 0, 20, 15), (20, 15, 35, 15),
        (35, 15, 35, 45), (35, 45, 55, 45), (55, 45, 55, 15),
    ]
    for x1, y1, x2, y2 in lines:
        draw.line(
            [(x + sx * x1, y + sy * y1), (x + sx * x2, y + sy * y2)],
            fill=GOLD, width=3,
        )


def _draw_triangle_corner(img, corner):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    s = 300
    pts = {
        "tl": [(0, 0),   (s, 0),   (0, s)],
        "tr": [(W, 0),   (W-s, 0), (W, s)],
        "bl": [(0, H),   (s, H),   (0, H-s)],
        "br": [(W, H),   (W-s, H), (W, H-s)],
    }[corner]
    d.polygon(pts, fill=NAVY + (255,))
    img.alpha_composite(overlay)


def _rounded_medal(draw, cx, cy, r, label_lines):
    points = []
    n = 24
    for i in range(n * 2):
        rad = r if i % 2 == 0 else r - 14
        ang = math.pi * i / n
        points.append((cx + rad * math.sin(ang), cy - rad * math.cos(ang)))
    draw.polygon(points, fill=GOLD)
    draw.ellipse([cx - r + 10, cy - r + 10, cx + r - 10, cy + r - 10], fill=GOLD_LIGHT)
    draw.ellipse([cx - r + 22, cy - r + 22, cx + r - 22, cy + r - 22], fill=NAVY)

    f1 = _font(F_SANS_BOLD, 22)
    f2 = _font(F_SANS_BOLD, 30)
    y = cy - 45
    for i, line in enumerate(label_lines):
        f = f2 if i == len(label_lines) - 1 else f1
        w = _text_w(draw, line, f)
        draw.text((cx - w / 2, y), line, font=f, fill=GOLD_LIGHT)
        y += 34

    ribbon_w = 90
    draw.polygon(
        [
            (cx - ribbon_w / 2, cy + r - 20),
            (cx + ribbon_w / 2, cy + r - 20),
            (cx + ribbon_w / 2, cy + r + 260),
            (cx, cy + r + 220),
            (cx - ribbon_w / 2, cy + r + 260),
        ],
        fill=NAVY,
    )
    draw.rectangle([cx - ribbon_w / 2 - 14, cy + r - 20, cx - ribbon_w / 2 - 4, cy + r + 250], fill=GOLD)
    draw.rectangle([cx + ribbon_w / 2 + 4,  cy + r - 20, cx + ribbon_w / 2 + 14, cy + r + 250], fill=GOLD)


# ----------------------------------------------------------------------
# ASOSIY FUNKSIYA
# ----------------------------------------------------------------------

def generate_certificate(
    full_name: str,
    percent: int,
    correct: int,
    total: int,
    cert_id: str = None,
    date_str: str = None,
    exam_title: str = "PREZIDENT MAKTABI MATEMATIKA & IQ TEST",
    exam_sub: str = "AKADEMIK SINOVIDA",
    org_name: str = "ASILBEK MATH",
    org_sub: str = "PREZIDENT MAKTABLARIGA TAYYORLOV PLATFORMASI",
    signer_name: str = "NURIDDINOV ASILBEK",
    signer_role: str = "LOYIHA RAHBARI",
    signature_text: str = "Asilbek",
    output_dir: str = None,
) -> str:
    """
    Diplom rasmini yaratadi va fayl yo'lini qaytaradi (PNG, 1920x1280).
    """
    if output_dir is None:
        output_dir = str(Path("/tmp/certificates"))
    os.makedirs(output_dir, exist_ok=True)

    cert_id  = cert_id  or f"AM-{datetime.now().year}-{uuid.uuid4().hex[:4].upper()}"
    date_str = date_str or datetime.now().strftime("%d.%m.%Y")

    if percent >= 90:
        level_label = ["I DARAJALI", "G'OLIB"]
        badge_top, badge_bottom = "I DARAJALI", "G'OLIB"
    elif percent >= 75:
        level_label = ["II DARAJALI", "G'OLIB"]
        badge_top, badge_bottom = "II DARAJALI", "G'OLIB"
    elif percent >= 60:
        level_label = ["III DARAJALI", "G'OLIB"]
        badge_top, badge_bottom = "III DARAJALI", "G'OLIB"
    else:
        level_label = ["ISHTIROKCHI"]
        badge_top, badge_bottom = "ISHTIROKCHI", ""

    img  = Image.new("RGBA", (W, H), CREAM + (255,))
    draw = ImageDraw.Draw(img)

    # Ramkalar
    draw.rectangle([0, 0, W - 1, H - 1], outline=NAVY, width=14)
    draw.rectangle([34, 34, W - 34, H - 34], outline=GOLD, width=4)

    # Burchak uchburchaklari
    for c in ("tl", "tr", "bl", "br"):
        _draw_triangle_corner(img, c)
    draw = ImageDraw.Draw(img)

    # Burchak bezaklari
    _corner_ornament(draw, 40, 40)
    _corner_ornament(draw, W - 40, 40, flip_x=True)
    _corner_ornament(draw, 40, H - 40, flip_y=True)
    _corner_ornament(draw, W - 40, H - 40, flip_x=True, flip_y=True)

    # Chap lenta
    ribbon_x = 230
    draw.rectangle([ribbon_x - 55, 0, ribbon_x - 25, H], fill=GOLD)
    draw.rectangle([ribbon_x - 20, 0, ribbon_x + 90, H], fill=NAVY)
    draw.rectangle([ribbon_x + 95, 0, ribbon_x + 125, H], fill=GOLD)

    # Medal
    _rounded_medal(draw, ribbon_x + 35, 330, 145, level_label)

    # Markaziy kontent
    cx = (W + 380) // 2

    f_logo_title = _font(F_SANS_BOLD, 46)
    f_logo_sub   = _font(F_SANS_BOLD, 18)
    f_diplom     = _font(F_SERIF_BOLD, 130)
    f_line_label = _font(F_SANS, 26)
    f_name       = _font(F_SERIF_BOLD, 56)
    f_exam       = _font(F_SANS_BOLD, 26)
    f_exam_sub   = _font(F_SANS_BOLD, 20)
    f_stat_num   = _font(F_SERIF_BOLD, 54)
    f_stat_lbl   = _font(F_SANS_BOLD, 16)
    f_footer_lbl = _font(F_SANS_BOLD, 17)
    f_footer_val = _font(F_SANS_BOLD, 24)
    f_sign       = _font(F_SCRIPT, 58)
    f_roman      = _font(F_SERIF_BOLD, 40)

    y = 70

    # Logo romb
    diamond_r  = 34
    diamond_cx = cx - _text_w(draw, org_name, f_logo_title) / 2 - 60
    diamond_cy = y + 10 + diamond_r
    _draw_diamond_logo(draw, diamond_cx, diamond_cy, diamond_r)

    _center_text(draw, cx + 40, y,      org_name, f_logo_title, NAVY,     tracking=6)
    y += 62
    _center_text(draw, cx + 40, y,      org_sub,  f_logo_sub,   TEXT_GOLD, tracking=2)
    y += 40
    draw.line([(cx - 260, y), (cx + 340, y)], fill=GOLD, width=2)
    y += 30

    _center_text(draw, cx, y, "DIPLOM", f_diplom, NAVY, tracking=14)
    y += 175
    draw.line([(cx - 260, y), (cx + 340, y)], fill=GOLD, width=2)
    y += 30

    _center_text(
        draw, cx, y,
        "Ushbu diplom yuqori natija va bilimga intilishi uchun taqdim etiladi:",
        f_line_label, TEXT_DARK,
    )
    y += 55

    # Ism-familiya (2 qatorga avtomatik bo'linish)
    words = full_name.upper().split()
    line1, line2 = full_name.upper(), ""
    max_w = 900
    if _text_w(draw, full_name.upper(), f_name) > max_w:
        best = None
        for i in range(1, len(words)):
            l1 = " ".join(words[:i])
            l2 = " ".join(words[i:])
            score = max(_text_w(draw, l1, f_name), _text_w(draw, l2, f_name))
            if best is None or score < best[0]:
                best = (score, l1, l2)
        _, line1, line2 = best

    _center_text(draw, cx, y, line1, f_name, NAVY)
    y += 66
    if line2:
        _center_text(draw, cx, y, line2, f_name, NAVY)
        y += 66
    y += 10

    draw.line([(cx - 220, y), (cx + 300, y)], fill=GOLD, width=2)
    y += 26
    _center_text(draw, cx, y, f'"{exam_title}"', f_exam, NAVY, tracking=1)
    y += 36
    _center_text(draw, cx, y, exam_sub, f_exam_sub, TEXT_GOLD, tracking=3)
    y += 70

    # Statistik bloklar
    stats = [
        (f"{percent}%",        "UMUMIY NATIJA"),
        (f"{correct}/{total}", "TO'G'RI JAVOB"),
    ]
    block_w = 260
    start_x = cx - block_w * 1.5 + 40
    for i, (num, lbl) in enumerate(stats):
        bx = start_x + i * block_w
        _center_text(draw, bx, y,      num, f_stat_num, NAVY)
        _center_text(draw, bx, y + 68, lbl, f_stat_lbl, TEXT_GOLD, tracking=1)
        draw.line([(bx + block_w / 2, y - 6), (bx + block_w / 2, y + 78)], fill=GOLD, width=2)

    # Laurel + daraja
    lx  = start_x + len(stats) * block_w + 40
    lcy = y + 34
    _draw_laurel_wreath(img, lx, lcy + 44, n=6, maxR=30, height=58)
    draw = ImageDraw.Draw(img)
    _center_text(draw, lx, lcy - 18, "I", f_roman, TEXT_GOLD)
    tx = lx + 70
    draw.text((tx, y + 4),  badge_top,    font=_font(F_SANS_BOLD, 24), fill=NAVY)
    if badge_bottom:
        draw.text((tx, y + 34), badge_bottom, font=_font(F_SANS_BOLD, 24), fill=NAVY)

    y += 130
    draw.line([(cx - 340, y), (cx + 440, y)], fill=GOLD, width=2)
    y += 34

    # Footer
    fx = cx - 340
    draw.text((fx, y - 6), "SERTIFIKAT ID:",  font=f_footer_lbl, fill=(90, 90, 90))
    draw.text((fx, y + 20), cert_id,           font=f_footer_val, fill=NAVY)

    fx2 = cx - 30
    draw.text((fx2, y - 6), "BERILGAN SANA:", font=f_footer_lbl, fill=(90, 90, 90))
    draw.text((fx2, y + 20), date_str,         font=f_footer_val, fill=NAVY)

    # Imzo
    sig_x = cx + 300
    _center_text(draw, sig_x, y - 20, signature_text, f_sign, NAVY)
    draw.line([(sig_x - 130, y + 46), (sig_x + 130, y + 46)], fill=(60, 60, 60), width=2)
    _center_text(draw, sig_x, y + 54, signer_role, _font(F_SANS_BOLD, 15), (90, 90, 90), tracking=1)
    _center_text(draw, sig_x, y + 74, signer_name, _font(F_SANS_BOLD, 20), NAVY, tracking=1)

    # QR kod (chap pastda)
    try:
        import qrcode
        qr = qrcode.QRCode(border=1, box_size=6)
        qr.add_data(f"CERT:{cert_id}")
        qr.make(fit=True)
        qimg = qr.make_image(fill_color=NAVY, back_color=CREAM).convert("RGBA")
        qimg = qimg.resize((190, 190))
        img.paste(qimg, (ribbon_x + 160, H - 260), qimg)
        draw = ImageDraw.Draw(img)
        draw.rectangle(
            [ribbon_x + 150, H - 270, ribbon_x + 360, H - 60], outline=GOLD, width=2
        )
    except ImportError:
        pass

    out_path = os.path.join(output_dir, f"certificate_{cert_id}.png")
    img.convert("RGB").save(out_path, "PNG", quality=95)
    return out_path
