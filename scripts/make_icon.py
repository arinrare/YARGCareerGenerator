"""Generate the application icon (assets/icon.png + assets/icon.ico).

Source: assets/guitar.svg (CC0 public domain — acoustic guitar from Open Clip Art
Library by narrowhouse, retrieved via Wikimedia Commons). See assets/ATTRIBUTION.md.

Renders the guitar as a white silhouette on the app's purple rounded-square
background. Requires PySide6 (SVG rasterisation) and Pillow (compositing + ICO).

Run from the repository root:
    .venv\\Scripts\\python.exe scripts\\make_icon.py
"""

import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SVG = ASSETS / "guitar.svg"
PNG = ASSETS / "icon.png"
ICO = ASSETS / "icon.ico"

ACCENT_TOP = (138, 111, 255)     # #8a6fff
ACCENT_BOTTOM = (107, 79, 230)   # #6b4fe6
SIZE = 512
CORNER_RADIUS = int(SIZE * 0.22)
GUITAR_FILL = 0.78  # guitar height as a fraction of the canvas


def _svg_default_size(svg_path):
    from PySide6.QtSvg import QSvgRenderer
    return QSvgRenderer(str(svg_path)).defaultSize()


def _render_svg_png_bytes(svg_path, width, height):
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtCore import QRectF, QBuffer

    img = QImage(width, height, QImage.Format_ARGB32)
    img.fill(0)
    painter = QPainter(img)
    QSvgRenderer(str(svg_path)).render(painter, QRectF(0, 0, width, height))
    painter.end()

    buf = QBuffer()
    buf.open(QBuffer.ReadWrite)
    img.save(buf, "PNG")
    return io.BytesIO(bytes(buf.data()))


def make_icon():
    from PIL import Image, ImageDraw

    default = _svg_default_size(SVG)
    scale = (SIZE * GUITAR_FILL) / default.height()
    gw = max(int(default.width() * scale), 1)
    gh = max(int(default.height() * scale), 1)

    guitar = Image.open(_render_svg_png_bytes(SVG, gw, gh)).convert("RGBA")

    # White silhouette driven by the source alpha channel.
    white = Image.new("RGBA", guitar.size, (255, 255, 255, 255))
    white.putalpha(guitar.split()[3])

    # Rounded-square background with a vertical purple gradient.
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    grad = Image.new("RGBA", (SIZE, SIZE))
    draw = ImageDraw.Draw(grad)
    for y in range(SIZE):
        t = y / (SIZE - 1)
        color = tuple(
            int(ACCENT_TOP[i] + (ACCENT_BOTTOM[i] - ACCENT_TOP[i]) * t) for i in range(3)
        ) + (255,)
        draw.line([(0, y), (SIZE - 1, y)], fill=color)

    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, SIZE - 1, SIZE - 1], radius=CORNER_RADIUS, fill=255
    )
    canvas.paste(grad, (0, 0), mask)

    # Center the guitar on the background.
    canvas.alpha_composite(white, ((SIZE - gw) // 2, (SIZE - gh) // 2))

    canvas.save(PNG)

    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    canvas.resize((256, 256), Image.LANCZOS).save(ICO, format="ICO", sizes=sizes)

    print(f"Wrote {PNG}")
    print(f"Wrote {ICO}")


if __name__ == "__main__":
    make_icon()
