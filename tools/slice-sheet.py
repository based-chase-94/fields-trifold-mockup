#!/usr/bin/env python3
"""
Fields trifold — cut press-sheet artwork into the six panel files the viewer wants.

Two ways in.

**A layered PSD holding both sides** (the usual case — one file with an
INTERIOR group and an EXTERIOR group, only one of them visible):

    python3 tools/slice-sheet.py --psd Fields-Trifold.psd

Both sides are rendered and sliced, whichever one was left visible when the
file was saved. Check what it found first with:

    python3 tools/slice-sheet.py --psd Fields-Trifold.psd --list

and name the groups yourself if the guess is wrong:

    python3 tools/slice-sheet.py --psd Fields-Trifold.psd \
            --outside-group EXTERIOR --inside-group INTERIOR

**Two sheet exports, one per side** — PDF, or jpg/png/tif:

    python3 tools/slice-sheet.py --outside Outside.pdf --inside Inside.pdf

Either way it writes images/exterior_01..03.jpg and images/interior_01..03.jpg.
Panel order is left-to-right as the sheet prints:

    outside  ->  exterior_01 tuck flap | exterior_02 back cover | exterior_03 front cover
    inside   ->  interior_01 inside 1  | interior_02 inside 2   | interior_03 inside 3

CMYK is converted to sRGB.

**Bleed.** A print export is bigger than the finished piece: the artwork runs
past the cut so the trim can wander. Those extra millimetres are not part of
any panel, and slicing a sheet with the bleed still on puts every fold off by
half a bleed - visibly, by about 22px on a 1/16in bleed at 350 dpi.

A PDF states its page size, so the bleed is measured and removed: the page is
cropped to a centred 11 x 8.5 before the panels are cut. --no-trim keeps the
full sheet, --trim 11x8.5 sets a different finished size.

A raster says nothing about its own size, so there the bleed has to be given:
--bleed 0.0625 (inches per edge).

Panels are cut as equal thirds. A real letter trifold makes the tuck flap a
hair narrower so it clears the fold; if your art is imposed that way, pass the
three trimmed widths in pixels instead: --widths 1312,1293,1289
"""

import argparse
import pathlib
import re
import sys

try:
    from PIL import Image
except ModuleNotFoundError:
    sys.exit("Pillow is needed:  python3 -m pip install --user Pillow")

Image.MAX_IMAGE_PIXELS = None          # press-sheet scans are legitimately huge

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "images"

SIDES = {
    "outside": ("exterior", ("tuck flap", "back cover", "front cover")),
    "inside":  ("interior", ("inside 1", "inside 2", "inside 3")),
}

# How a top-level PSD group announces which side of the sheet it is.
SIDE_WORDS = {
    "outside": ("exterior", "outside", "exterior side", "outer", "front side", "cover"),
    "inside":  ("interior", "inside", "interior side", "inner", "back side", "spread"),
}

PANEL_RATIO = 8.5 / 3.667               # 2.318 — a letter trifold panel
TRIM = (11.0, 8.5)                      # finished sheet, inches
PDF_SUFFIXES = {".pdf"}


def pdf_sheet(path, dpi, trim):
    """Rasterise a one-page PDF, cropping the bleed off first.

    A print export is larger than the finished piece. Illustrator and
    Photoshop often write the same rectangle into every page box, so there is
    no TrimBox to believe - but the page size is still real, and the artwork
    is centred in it, so the bleed is just the overhang halved.
    """
    try:
        import fitz                     # PyMuPDF
    except ModuleNotFoundError:
        sys.exit("Reading a PDF needs PyMuPDF:\n"
                 "    python3 -m pip install --user pymupdf")

    doc = fitz.open(path)
    if doc.page_count != 1:
        print(f"  note: {path.name} has {doc.page_count} pages - using the first")
    page = doc[0]
    rect = page.rect
    w_in, h_in = rect.width / 72, rect.height / 72
    print(f"  page {rect.width:.2f} x {rect.height:.2f} pt "
          f"= {w_in:.3f} x {h_in:.3f} in")

    clip = rect
    if trim:
        tw, th = trim
        bw, bh = (w_in - tw) / 2, (h_in - th) / 2
        if bw < -0.001 or bh < -0.001:
            print(f"  !! page is smaller than the {tw} x {th} in trim - "
                  f"not cropping. Check --trim.")
        elif bw < 0.001 and bh < 0.001:
            print(f"  no bleed: page already {tw} x {th} in")
        else:
            if abs(bw - bh) > 0.01:
                print(f"  !! bleed differs by axis ({bw:.4f} in across, "
                      f"{bh:.4f} in down) - the artwork may not be centred")
            print(f"  bleed {bw:.4f} in per edge -> cropping to {tw} x {th} in")
            clip = fitz.Rect(bw * 72, bh * 72,
                             rect.width - bw * 72, rect.height - bh * 72)

    pix = page.get_pixmap(dpi=dpi, clip=clip, colorspace=fitz.csRGB, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    print(f"  rendered at {dpi} dpi -> {img.width} x {img.height}")
    return img


def load_psd(path):
    try:
        from psd_tools import PSDImage
    except ModuleNotFoundError:
        sys.exit("Reading a layered PSD needs psd-tools:\n"
                 "    python3 -m pip install --user psd-tools")
    print(f"opening {path.name} ...")
    return PSDImage.open(path)


def top_groups(psd):
    return [L for L in psd if L.is_group()]


def guess_group(psd, side):
    """Find the top-level group that looks like this side of the sheet."""
    words = SIDE_WORDS[side]
    for layer in top_groups(psd):
        name = re.sub(r"[^a-z ]", " ", layer.name.lower()).strip()
        if any(re.search(rf"\b{w}\b", name) for w in words):
            return layer
    return None


def render_group(psd, group):
    """Composite one top-level group alone, over the full sheet canvas."""
    state = {id(L): L.visible for L in psd}
    try:
        for layer in psd:
            if layer.is_group():
                # Only the side we want. Anything else at the top level
                # (a Background fill, a paper texture) stays as it was.
                layer.visible = layer is group
        img = psd.composite()
    finally:
        for layer in psd:
            layer.visible = state[id(layer)]
    return img


def to_rgb(im):
    if getattr(im, "n_frames", 1) > 1:
        im.seek(0)                      # .psd flattened composite
    if im.mode == "RGBA":
        # Composites come back with alpha. Flatten onto white so the
        # transparent margin round the artwork doesn't save as black.
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im if im.mode == "RGB" else im.convert("RGB")


def debleed(im, bleed_in):
    """Trim `bleed_in` inches off every edge, measuring dpi off the sheet."""
    if not bleed_in:
        return im
    w, h = im.size
    dpi = w / (11.0 + 2 * bleed_in)     # sheet is 11 in wide plus bleed each side
    cut = round(bleed_in * dpi)
    print(f"  bleed {bleed_in}in at {dpi:.0f} dpi -> trimming {cut}px per edge")
    return im.crop((cut, cut, w - cut, h - cut))


def cut(im, side, widths, quality, out, label_src):
    stem, labels = SIDES[side]
    im = to_rgb(im)
    w, h = im.size

    if widths:
        if sum(widths) != w:
            sys.exit(f"{label_src}: --widths sums to {sum(widths)} but the "
                     f"trimmed sheet is {w}px wide")
        edges = [0]
        for x in widths:
            edges.append(edges[-1] + x)
    else:
        # Integer thirds that always add back up to w - no dropped column.
        edges = [round(w * i / 3) for i in range(4)]

    print(f"{label_src}: {w} x {h}  ({w/h:.3f} : 1)")
    out.mkdir(parents=True, exist_ok=True)
    off = []
    for i, label in enumerate(labels):
        dest = out / f"{stem}_{i + 1:02d}.jpg"
        panel = im.crop((edges[i], 0, edges[i + 1], h))
        panel.save(dest, "JPEG", quality=quality, subsampling=0,
                   optimize=True, progressive=True)
        pw, ph = panel.size
        ratio = ph / pw
        try:
            shown = dest.relative_to(ROOT)
        except ValueError:
            shown = dest
        flag = "" if abs(ratio - PANEL_RATIO) < 0.06 else "   <-- off"
        off.append(bool(flag))
        print(f"  -> {shown}  {pw} x {ph}  ({ratio:.3f} tall)  {label}{flag}")
    return any(off)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--psd", type=pathlib.Path,
                    help="layered PSD holding both sides")
    ap.add_argument("--list", action="store_true",
                    help="with --psd: show the top-level groups and stop")
    ap.add_argument("--outside-group", help="with --psd: group to render as the outside")
    ap.add_argument("--inside-group", help="with --psd: group to render as the inside")
    ap.add_argument("--outside", type=pathlib.Path,
                    help="outside sheet — pdf, jpg, png, tif")
    ap.add_argument("--inside", type=pathlib.Path,
                    help="inside sheet — pdf, jpg, png, tif")
    ap.add_argument("--widths", help="three panel widths in px, comma separated")
    ap.add_argument("--bleed", type=float, default=0.0,
                    help="raster sheets: inches of bleed per edge to trim off")
    ap.add_argument("--dpi", type=int, default=300,
                    help="pdf sheets: render resolution (default 300)")
    ap.add_argument("--trim", default="11x8.5",
                    help="pdf sheets: finished size in inches (default 11x8.5)")
    ap.add_argument("--no-trim", action="store_true",
                    help="pdf sheets: keep the bleed, slice the whole page")
    ap.add_argument("--quality", type=int, default=88, help="JPEG quality (default 88)")
    ap.add_argument("--out", type=pathlib.Path, default=OUT,
                    help="where to write the panels (default images/)")
    a = ap.parse_args()

    if not (a.psd or a.outside or a.inside):
        ap.error("give --psd, or --outside/--inside")

    widths = None
    if a.widths:
        widths = [int(x) for x in a.widths.split(",")]
        if len(widths) != 3:
            ap.error("--widths needs exactly three numbers")

    suspect = False

    if a.psd:
        if not a.psd.exists():
            sys.exit(f"not found: {a.psd}")
        psd = load_psd(a.psd)
        groups = top_groups(psd)

        if a.list:
            mode = getattr(psd.color_mode, "name", psd.color_mode)
            print(f"\n{a.psd.name} — {psd.size[0]} x {psd.size[1]}, {mode}")
            print("top-level groups:")
            for g in groups:
                print(f"  {g.name!r}   visible={g.visible}")
            print("\nPass the ones you want as --outside-group / --inside-group.")
            return

        if not groups:
            sys.exit(f"{a.psd.name} has no top-level groups. Treat it as a flat "
                     f"sheet instead:  --outside {a.psd}")

        by_name = {g.name: g for g in groups}
        chosen = {}
        for side, flag in (("outside", a.outside_group), ("inside", a.inside_group)):
            if flag:
                if flag not in by_name:
                    sys.exit(f"no top-level group named {flag!r}. Found: "
                             + ", ".join(repr(g.name) for g in groups))
                chosen[side] = by_name[flag]
            else:
                g = guess_group(psd, side)
                if g is not None:
                    chosen[side] = g

        if not chosen:
            sys.exit("Could not tell which groups are the two sides. Run with "
                     "--list and name them with --outside-group / --inside-group.")

        for side in ("outside", "inside"):
            if side not in chosen:
                print(f"note: no {side} group found — skipping that side")
                continue
            g = chosen[side]
            print(f"\nrendering {side} from group {g.name!r} "
                  f"(this takes a moment on a large file) ...")
            im = debleed(render_group(psd, g), a.bleed)
            suspect |= cut(im, side, widths, a.quality, a.out,
                           f"{a.psd.name} [{g.name}]")

    trim = None
    if not a.no_trim:
        try:
            tw, th = (float(x) for x in a.trim.lower().split("x"))
            trim = (tw, th)
        except ValueError:
            ap.error("--trim wants a size like 11x8.5")

    for side in ("outside", "inside"):
        path = getattr(a, side)
        if not path:
            continue
        if not path.exists():
            sys.exit(f"not found: {path}")
        print(f"\n{path.name} ({side})")
        if path.suffix.lower() in PDF_SUFFIXES:
            im = pdf_sheet(path, a.dpi, trim)
            if a.bleed:
                print("  note: --bleed ignored for a PDF — the page size is "
                      "measured instead")
        else:
            im = debleed(Image.open(path), a.bleed)
        suspect |= cut(im, side, widths, a.quality, a.out, path.name)

    if suspect:
        print(f"\n!! Some panels are far from the {PANEL_RATIO:.3f} tall a letter "
              f"trifold panel should be.\n   The sheet may carry bleed (--bleed "
              f"0.125), or not be an 11 x 8.5 trifold at all.\n   Check the files "
              f"before trusting them.")
    else:
        print(f"\nAll panels near {PANEL_RATIO:.3f} tall, as a letter trifold "
              f"panel should be.")


if __name__ == "__main__":
    main()
