# Fields — Trifold Menu Mockup

Rotate the folded piece, scrub it open, and check the imposition. Open
`index.html` in any browser — no build step, no server, no dependencies.

Same tool as [`woodgrain-trifold-mockup`](https://github.com/based-chase-94/woodgrain-trifold-mockup),
rethemed to the Fields palette.

## Artwork status

**Live artwork is in**, cut from `trifold-exterior.pdf` / `trifold-interior.pdf`
(exported from `Trifold-Menu.psd`, 21 Oct 2026) at 300 dpi — 1100 × 2551 per
panel. Rebuild them any time with:

```bash
python3 tools/slice-sheet.py \
  --outside "…/Fields/trifold-exterior.pdf" \
  --inside  "…/Fields/trifold-interior.pdf"
```

Those PDFs are **11.126 × 8.626 in** — the 11 × 8.5 finished sheet plus a
uniform 1/16 in bleed per edge, and *every* page box says the same thing, so
nothing downstream can tell the bleed from the artwork. The tool measures it
off the page size and crops before it cuts. Skip that step and all four folds
land ~22 px adrift.

If a panel file is ever missing, that panel falls back to a stand-in in
`images/placeholder/` and a bar under the header names what it wants.

## Dropping the artwork in

Put six files in `images/` with these names and reload. No code change needed —
any format the browser reads works (jpg, png, svg, webp).

| File | Panel |
|---|---|
| `images/exterior_01.jpg` | outside left — tuck-in flap |
| `images/exterior_02.jpg` | outside middle — back cover |
| `images/exterior_03.jpg` | outside right — front cover |
| `images/interior_01.jpg` | inside left — reverse of the front cover |
| `images/interior_02.jpg` | inside middle — reverse of the back cover |
| `images/interior_03.jpg` | inside right — reverse of the tuck flap |

To keep your own filenames instead, edit the `ART` block at the top of the
`<script>` in `index.html` — it maps each panel to a path. Rename the matching
file in `images/placeholder/` to suit and the fallback keeps working.

### From the layered PSD — the usual case

A trifold working file holds **both sides in one document**, as two top-level
groups, with only one of them visible at a time. Hand the whole file over:

```bash
python3 tools/slice-sheet.py --psd Fields-Trifold.psd
```

It finds the two side groups by name, renders each one on its own — including
the one that was switched off when the file was saved — converts CMYK to sRGB,
and writes all six panels. Expect roughly half a minute on a large file.

Look before you leap:

```bash
python3 tools/slice-sheet.py --psd Fields-Trifold.psd --list
```

That prints the top-level groups and stops. If the guess is wrong, or the
groups aren't called anything like "interior" and "exterior", name them:

```bash
python3 tools/slice-sheet.py --psd Fields-Trifold.psd \
        --outside-group EXTERIOR --inside-group INTERIOR
```

The PSD path needs `psd-tools`; the tool says so if it's missing.

```bash
python3 -m pip install --user psd-tools
```

### From one-sided exports — what's in use now

A PDF per side is the cleanest route, because a PDF states its own page size
and the bleed can be measured rather than guessed:

```bash
python3 tools/slice-sheet.py --outside Outside.pdf --inside Inside.pdf
```

Rasters work the same way, but a jpg says nothing about its finished size, so
there the bleed has to be given: `--bleed 0.0625`.

### Options

| Flag | What it does |
|---|---|
| `--dpi 300` | PDF render resolution |
| `--trim 11x8.5` | PDF finished size; the overhang is cropped as bleed |
| `--no-trim` | PDF: keep the bleed, slice the whole page |
| `--bleed 0.0625` | rasters: inches per edge to trim before cutting |
| `--widths 1312,1293,1289` | cuts uneven panels, for art imposed with a narrower tuck flap |
| `--out some/dir` | writes somewhere else, to look over before going live |
| `--quality 88` | JPEG quality |

It prints each panel's height-to-width ratio as it goes and flags any that
stray. A letter panel should land near **2.318**; a long way off means the
sheet carries bleed, or isn't an 11 × 8.5 trifold at all — and the thirds are
cutting through the artwork rather than along the folds.

## Panel map — letter fold

Both creases bend the same way, so the sheet curls into a "C" and the flap
nests inside the cover. (A Z-fold, where the creases alternate, would expose
that panel on the back instead — not what this piece is built for.)

Printed on one sheet: the outside spread on the front, the inside spread on the
back. The tuck flap folds in first, the front cover folds over it.

So when you open the front cover you see inside panel 1 on the left and the
*outside* of the tuck flap on the right; open the flap and the full
three-panel spread is revealed.

Artwork is 3.667 in × 8.5 in per panel — a letter sheet, 11 × 8.5, folded in
thirds. That's 1100 × 2550 px at 300 dpi. The mockup renders all three panels
at equal width, so if the exports differ slightly per panel (a real trifold
makes the tuck flap a hair narrower so it clears the fold) that difference is
ignored here.

## Colour

From **Fields Brand Guidelines, p.12**. Nothing in the chrome carries a colour
that isn't on that page.

| | Name | HEX | Used for |
|---|---|---|---|
| ⬛ | Forest | `#283628` | placeholder ground |
| 🟨 | Sunshine | `#F9E14D` | active buttons, fold lines, placeholder numerals |
| 🟧 | Poppy | `#E84A28` | placeholder trim rules |
| 🟥 | Burgundy | `#5F2637` | the artwork-pending bar |
| ⬜ | Almond | `#F4E9E1` | all UI text |

Sunshine only ever sits behind dark ink — Forest on Sunshine measures 9.7:1,
and Sunshine on anything light is invisible (1.12:1 on the website's page
colour). That rule is why the active-button state is Forest *on* Sunshine
rather than the other way round.

## Controls

- **Slide to fold / unfold** — scrub from flat open to fully closed
- **Closed / Cover open / Fully open** — animated presets
- **Flip over** — spin to the other side
- **Labels** — panel name overlays
- **Press sheet** — flat imposition view showing both sides with fold lines
- **Drag** to rotate, **scroll** to zoom. The view auto-fits whatever the fold
  is showing, so the closed cover fills the frame and the open spread pulls back

The slider deliberately sits on its own row rather than at the very top of the
page: Arc keeps a window-drag strip along the top edge of the web view, and a
control up there drags the browser window instead of the handle.

The mockup is view-only — a viewer can't alter the artwork from the page.

## Run it over HTTP

Not needed — the page works straight off disk — but closer to how a host would
serve it:

```bash
python3 tools/serve.py
```

Then open <http://localhost:8124/>.

## Repo layout

Code lives here in `~/Developer`; the artwork masters stay in Tresorit.
`artwork-path.local` records which client folder this piece belongs to. It is
gitignored, because it holds a path off one particular machine — so a fresh
clone won't have it. Write it again if you need it:

```bash
echo "/path/to/Freelance Clients/Fields" > artwork-path.local
```

## Publishing

**GitHub Pages is not enabled for this repo**, so nothing is served from it —
the repo is source only, and you view it by opening `index.html` locally. The
repo itself is public, so treat the artwork in `images/` as published.

`.nojekyll` and `robots.txt` are kept so Pages works correctly the day it's
switched on, and the page already carries a `noindex, nofollow` meta tag. None
of that makes anything private: a public repo is readable by anyone, and if
Pages is ever enabled, anyone with the URL can open the page. See `robots.txt`
for why a `Disallow` would make that worse rather than better.
