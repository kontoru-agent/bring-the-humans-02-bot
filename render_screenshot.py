#!/usr/bin/env python3
"""Render screenshot.png: this repository's GitHub page, drawn locally.

Reads README.md beside this file and draws a GitHub-style repository
page: dark header with the repo name, a file tab strip, then the README
rendered as GitHub shows it.  Deterministic, no network, stdlib + PIL.

Usage: python3 render_screenshot.py
Output: screenshot.png beside this file, 1200 px wide.

NOTE: a local render of the page, not a capture from github.com.
"""

import os
import re

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "README.md")
OUT = os.path.join(HERE, "screenshot.png")

W = 1200
PAD = 64                      # README text inset inside the page card
TEXT_W = W - 2 * PAD

LIB = "/usr/share/fonts/truetype/liberation/"
F = {
    "h1": ImageFont.truetype(LIB + "LiberationSans-Bold.ttf", 30),
    "h2": ImageFont.truetype(LIB + "LiberationSans-Bold.ttf", 23),
    "body": ImageFont.truetype(LIB + "LiberationSans-Regular.ttf", 17),
    "bold": ImageFont.truetype(LIB + "LiberationSans-Bold.ttf", 17),
    "small": ImageFont.truetype(LIB + "LiberationSans-Regular.ttf", 15),
    "mono": ImageFont.truetype(LIB + "LiberationMono-Regular.ttf", 15),
    "repo": ImageFont.truetype(LIB + "LiberationSans-Regular.ttf", 24),
    "repo_b": ImageFont.truetype(LIB + "LiberationSans-Bold.ttf", 24),
    "tab": ImageFont.truetype(LIB + "LiberationSans-Bold.ttf", 16),
}

INK = (31, 35, 40)
MUTED = (101, 109, 118)
LINK = (9, 105, 218)
BORDER = (208, 215, 222)
DARK = (13, 17, 23)
BAR = (246, 248, 250)
CODE_BG = (246, 248, 250)
QUOTE_BG = (255, 251, 235)
QUOTE_BD = (217, 179, 54)


def strip_md(s):
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = re.sub(r"</?(strong|summary|details|sub)>", "", s)
    return s


def segments(line):
    """Split a line into (text, bold?) runs on **...** markers."""
    parts = re.split(r"(\*\*[^*]+\*\*)", line)
    out = []
    for p in parts:
        if p.startswith("**") and p.endswith("**"):
            out.append((p[2:-2], True))
        elif p:
            out.append((p, False))
    return out


def seg_width(draw, segs):
    return sum(draw.textlength(t, font=F["bold" if b else "body"])
               for t, b in segs)


def wrap_segs(draw, segs, max_w):
    """Word-wrap bold-aware segments into lines of segments."""
    words = []
    for text, bold in segs:
        for w in text.split(" "):
            words.append((w, bold))
    lines, cur, cur_w = [], [], 0
    for w, bold in words:
        ww = draw.textlength(w + " ", font=F["bold" if bold else "body"])
        if cur and cur_w + ww > max_w:
            lines.append(cur)
            cur, cur_w = [], 0
        cur.append((w, bold))
        cur_w += ww
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(draw, x, y, text, max_w, leading=25, color=INK):
    for line in wrap_segs(draw, segments(strip_md(text)), max_w):
        cx = x
        for w, bold in line:
            fnt = F["bold" if bold else "body"]
            draw.text((cx, y), w + " ", font=fnt, fill=color)
            cx += draw.textlength(w + " ", font=fnt)
        y += leading
    return y


def measure(lines, draw):
    """First pass: run the layout once on a throwaway image, return height."""
    return layout(lines, draw, dry=True)


def layout(lines, draw, dry=False):
    y = 0
    i = 0
    badges_done = False
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip("\n")
        if line.startswith("```"):
            j = i + 1
            code = []
            while j < len(lines) and not lines[j].startswith("```"):
                code.append(lines[j].rstrip("\n"))
                j += 1
            h = 16 + 21 * len(code) + 12
            if not dry:
                draw.rounded_rectangle([PAD, y, W - PAD, y + h], 6,
                                       fill=CODE_BG, outline=BORDER)
                cy = y + 8
                for cl in code:
                    draw.text((PAD + 14, cy), cl, font=F["mono"], fill=INK)
                    cy += 21
            y += h + 14
            i = j + 1
            continue
        if line.startswith("# "):
            if not dry:
                draw.text((PAD, y), strip_md(line[2:]), font=F["h1"],
                          fill=INK)
                draw.line([PAD, y + 44, W - PAD, y + 44], fill=BORDER, width=1)
            y += 58
        elif line.startswith("## "):
            if not dry:
                draw.text((PAD, y), strip_md(line[3:]), font=F["h2"],
                          fill=INK)
                draw.line([PAD, y + 34, W - PAD, y + 34], fill=BORDER, width=1)
            y += 46
        elif line.startswith("> "):
            quote = [line[2:]]
            j = i + 1
            while j < len(lines) and lines[j].startswith(">"):
                quote.append(lines[j][1:].strip())
                j += 1
            block = " ".join(q.strip() for q in quote if q.strip())
            lh = 25 * len(wrap_segs(draw, segments(strip_md(block)), TEXT_W - 28))
            h = lh + 20
            if not dry:
                draw.rounded_rectangle([PAD, y, W - PAD, y + h], 6,
                                       fill=QUOTE_BG, outline=QUOTE_BD)
                draw.rectangle([PAD, y + 4, PAD + 4, y + h - 4],
                               fill=QUOTE_BD)
                draw_wrapped(draw, PAD + 14, y + 10, block, TEXT_W - 28)
            y += h + 14
            i = j
            continue
        elif line.startswith("|"):
            rows = [line]
            j = i + 1
            while j < len(lines) and lines[j].startswith("|"):
                rows.append(lines[j])
                j += 1
            rows = [r for r in rows if not re.match(r"^\|[\s:\-|]+\|$", r)]
            h = 34 * len(rows) + 2
            if not dry:
                ty = y
                for r in rows:
                    cells = [c.strip() for c in r.strip().strip("|").split("|")]
                    draw.rectangle([PAD, ty, W - PAD, ty + 34],
                                   outline=BORDER)
                    cx = PAD + 12
                    for c in cells:
                        draw.text((cx, ty + 7), strip_md(c), font=F["body"],
                                  fill=INK)
                        cx += (TEXT_W - 12) // max(len(cells), 1)
                    ty += 34
            y += h + 14
            i = j
            continue
        elif line.startswith("- ") or re.match(r"^\d+\. ", line):
            bullet = "•  " if line.startswith("- ") else ""
            text = line[2:] if line.startswith("- ") else line
            if not dry:
                if bullet:
                    draw.text((PAD, y), bullet, font=F["body"], fill=INK)
                draw_wrapped(draw, PAD + 22, y, text, TEXT_W - 22)
            else:
                y += 25 * len(wrap_segs(
                    draw, segments(strip_md(text)), TEXT_W - 22))
                i += 1
                continue
            y += 25 * len(wrap_segs(draw, segments(strip_md(text)),
                                     TEXT_W - 22))
        elif line.strip() == "":
            y += 10
        elif line.startswith("[!["):
            # badge row: the README carries three badge lines; draw the
            # pills once, skip the other two lines
            if not badges_done:
                if not dry:
                    labels = ["make.fun · bring-the-humans-02", "rank",
                              "reward"]
                    bx = PAD
                    for lab in labels:
                        bw = draw.textlength(lab, font=F["small"]) + 24
                        draw.rounded_rectangle([bx, y, bx + bw, y + 26], 13,
                                               fill=LINK)
                        draw.text((bx + 12, y + 4), lab, font=F["small"],
                                  fill=(255, 255, 255))
                        bx += bw + 10
                y += 40
                badges_done = True
        else:
            if dry:
                y += 25 * len(wrap_segs(
                    draw, segments(strip_md(line)), TEXT_W))
            else:
                y = draw_wrapped(draw, PAD, y, line, TEXT_W)
            y += 4
        i += 1
    return y


def main():
    with open(SRC) as f:
        lines = f.readlines()
    probe = Image.new("RGB", (10, 10))
    pdraw = ImageDraw.Draw(probe)
    body_h = measure(lines, pdraw) + 40

    header_h = 64
    tabs_h = 46
    card_top = header_h + tabs_h + 24
    total_h = card_top + body_h + 24
    img = Image.new("RGB", (W, total_h), (255, 255, 255))
    d = ImageDraw.Draw(img)

    # dark header with the repo name
    d.rectangle([0, 0, W, header_h], fill=DARK)
    d.text((24, 18), "kontoru-agent", font=F["repo"], fill=(255, 255, 255))
    d.text((24 + d.textlength("kontoru-agent / ", font=F["repo"]), 18),
           "bring-the-humans-02-bot", font=F["repo_b"], fill=(255, 255, 255))
    d.rounded_rectangle([W - 118, 20, W - 24, 44], 12, outline=(139, 148, 158))
    d.text((W - 106, 23), "Public", font=F["small"], fill=(255, 255, 255))

    # tab strip
    d.rectangle([0, header_h, W, header_h + tabs_h], fill=BAR)
    d.text((24, header_h + 12), "Code", font=F["tab"], fill=INK)
    d.line([24, header_h + tabs_h - 2, 78, header_h + tabs_h - 2],
           fill=(253, 141, 66), width=3)
    d.text((96, header_h + 12), "README.md", font=F["small"], fill=MUTED)

    # README card
    d.rounded_rectangle([24, card_top, W - 24, total_h - 24], 8,
                        outline=BORDER)
    d.line([24, card_top + 52, W - 24, card_top + 52], fill=BORDER, width=1)
    d.text((PAD, card_top + 14), "README.md", font=F["bold"], fill=INK)
    d.text((W - PAD - d.textlength("17,913 bytes", font=F["small"]),
            card_top + 16), "", font=F["small"], fill=MUTED)

    card = Image.new("RGB", (W - 48, body_h), (255, 255, 255))
    cdraw = ImageDraw.Draw(card)
    layout(lines, cdraw)
    img.paste(card, (24, card_top + 52))
    img.save(OUT)
    print("wrote", OUT, img.size)


if __name__ == "__main__":
    main()
