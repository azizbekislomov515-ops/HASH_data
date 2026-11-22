"""Regenerate HashForge's original geometric bitmap icon (requires Pillow)."""

from pathlib import Path
from PIL import Image, ImageDraw


def main() -> None:
    """Draw a crisp hash mark over a forge-green tile and export ICO/PNG."""
    root = Path(__file__).resolve().parents[1] / "assets"
    root.mkdir(exist_ok=True)
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 248, 248), radius=40, fill="#202930")
    draw.polygon([(58, 178), (198, 178), (180, 206), (76, 206)], fill="#2cb5a4")
    for x in (99, 157):
        draw.line((x + 14, 51, x - 10, 161), fill="#f4f7f8", width=19)
    for y in (87, 130):
        draw.line((65, y, 195, y), fill="#f4f7f8", width=17)
    image.save(root / "icon.png")
    image.save(root / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
