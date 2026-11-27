"""Turn the simulator's .ppm frames into .png, plus one contact sheet (screens.png) at 2x."""
import sys
from pathlib import Path
from PIL import Image

out = Path(sys.argv[1])
frames = sorted(out.glob("*.ppm"))
imgs = []
for f in frames:
    im = Image.open(f).convert("RGB")
    im.save(f.with_suffix(".png"))
    imgs.append(im)
cols = 2
W, H, G = 320 * 2, 240 * 2, 16
sheet = Image.new("RGB", (cols * W + (cols + 1) * G, ((len(imgs) + cols - 1) // cols) * (H + G) + G), (40, 40, 40))
for i, im in enumerate(imgs):
    x, y = G + (i % cols) * (W + G), G + (i // cols) * (H + G)
    sheet.paste(im.resize((W, H), Image.NEAREST), (x, y))
sheet.save(out / "screens.png")
print("wrote", out / "screens.png")
