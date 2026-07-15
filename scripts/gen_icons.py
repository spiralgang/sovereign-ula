#!/usr/bin/env python3
"""Generate Sovereign ULA Android launcher + notification icons from sov_hero.jpeg.

Replaces every mipmap ic_launcher*.png and drawable-*dpi ic_stat_icon.png in the
app resources with resized crops of the bundled hero image, so the same artwork
represents the app everywhere (launcher, round icon, status-bar notification).

Adaptive-icon foreground: we crop a centered square of the hero and place it on a
transparent canvas at ~72% of the foreground layer size, leaving the adaptive
mask/background (defined in xml) to shape it. The legacy (non-adaptive) launcher
icons get a solid rounded backdrop so they read fine on old launchers.
"""
import os
from PIL import Image, ImageDraw, ImageFilter

# Pillow >= 10 renamed LANCZOS; fall back for older versions.
try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:  # Pillow < 10
    RESAMPLE = Image.LANCZOS

RES = "app/src/main/res"
SRC = "images/sov_hero.jpeg"

# density -> (legacy launcher px, round px, fg px, stat-bar px)
DENS = {
    "mdpi":    (48,  48,  48,  24),
    "hdpi":    (72,  72,  72,  36),
    "xhdpi":   (96,  96,  96,  48),
    "xxhdpi":  (144, 144, 144, 72),
    "xxxhdpi": (192, 192, 192, 96),
}

BACKDROP = (18, 22, 30)  # dark sovereign backdrop for legacy/round icons


def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def hero_square(img):
    """Center-crop the hero to a square, returned resized to given box."""
    w, h = img.size
    s = min(w, h)
    left = (w - s) // 2
    top = (h - s) // 2
    return img.crop((left, top, left + s, top + s))


def make_legacy(img_square, size):
    """Dark rounded-rect backdrop + circular hero inset."""
    base = Image.new("RGBA", (size, size), (*BACKDROP, 255))
    d = ImageDraw.Draw(base)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 5, fill=(*BACKDROP, 255))
    inset = int(size * 0.30)
    hero = hero_square(img_square).resize((size - 2 * inset, size - 2 * inset), Image.LANCZOS)
    # circular mask for the hero inset
    circ = Image.new("L", hero.size, 0)
    ImageDraw.Draw(circ).ellipse([0, 0, hero.size[0] - 1, hero.size[1] - 1], fill=255)
    base.paste(hero, (inset, inset), circ)
    return base


def make_foreground(img_square, size):
    """Centered circular hero on transparent (adaptive-icon foreground layer)."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inset = int(size * 0.14)
    hero = hero_square(img_square).resize((size - 2 * inset, size - 2 * inset), RESAMPLE)
    circ = Image.new("L", hero.size, 0)
    ImageDraw.Draw(circ).ellipse([0, 0, hero.size[0] - 1, hero.size[1] - 1], fill=255)
    canvas.paste(hero, (inset, inset), circ)
    return canvas


def make_stat(img_square, size):
    """Monochrome-ish small icon for the status bar (circular hero)."""
    hero = hero_square(img_square).resize((size, size), RESAMPLE).convert("RGBA")
    circ = Image.new("L", (size, size), 0)
    ImageDraw.Draw(circ).ellipse([0, 0, size - 1, size - 1], fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(hero, (0, 0), circ)
    return out


def main():
    img = Image.open(SRC).convert("RGBA")
    for dens, (sz, _, fg, st) in DENS.items():
        # legacy ic_launcher.png
        make_legacy(img, sz).save(f"{RES}/mipmap-{dens}/ic_launcher.png")
        # round icon (legacy) — full-bleed rounded square of hero
        base = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        hero = hero_square(img).resize((sz, sz), RESAMPLE)
        base.paste(hero, (0, 0), rounded_mask(sz, sz // 4))
        base.save(f"{RES}/mipmap-{dens}/ic_launcher_round.png")
        # adaptive foreground
        make_foreground(img, fg).save(f"{RES}/mipmap-{dens}/ic_launcher_foreground.png")
        # status-bar notification icon
        make_stat(img, st).save(f"{RES}/drawable-{dens}/ic_stat_icon.png")
        print(f"  {dens}: launcher/round/fg={sz}px  stat={st}px")
    print("Done.")


if __name__ == "__main__":
    main()
