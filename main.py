#!/usr/bin/env python3
"""News image: a newspaper front page summing up the world's news of
Tuesday 17 November 2026, drawn from scratch with a hand-written 5x7
bitmap font and a pure-stdlib PNG encoder. No network, no randomness,
no wall-clock time: two runs write byte-identical output."""

import os
import struct
import zlib

W, H = 1024, 1024

# Palette.
PAPER = (245, 240, 225)
INK = (18, 18, 18)
RED = (198, 32, 32)
NAVY = (28, 48, 88)
SEA = (38, 88, 138)
SKY = (198, 224, 244)
FIRE = (255, 170, 0)
EMBER = (255, 110, 0)
FLAME = (255, 222, 90)
GREEN = (38, 118, 60)
GREY = (150, 150, 150)
WHITE = (255, 255, 255)
BLUE = (40, 80, 180)

# 5x7 bitmap font. Each glyph is 7 rows of 5 bits, written as strings.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "11001", "10101", "10011", "10011", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10011", "10101", "11001", "10001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00010", "00100", "00100", "00100"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "01100", "01000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00001", "00010", "00100", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "&": ("01100", "10010", "10010", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
}


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def wrap(s, max_w, scale):
    words = s.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = (cur + " " + word).strip()
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


class Canvas:
    def __init__(self):
        self.px = bytearray(PAPER[0] for _ in range(W * H))
        self.px = bytearray(W * H * 3)
        for i in range(W * H):
            self.px[i * 3] = PAPER[0]
            self.px[i * 3 + 1] = PAPER[1]
            self.px[i * 3 + 2] = PAPER[2]

    def set_px(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def rect(self, x, y, w, h, c):
        x0 = max(x, 0)
        y0 = max(y, 0)
        x1 = min(x + w, W)
        y1 = min(y + h, H)
        for yy in range(y0, y1):
            base = (yy * W + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def line(self, x0, y0, x1, y1, c, w=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.rect(x0 - w // 2, y0 - w // 2, w, w, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, c):
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            dx = int((r * r - dy * dy) ** 0.5)
            self.rect(cx - dx, y, 2 * dx + 1, 1, c)

    def tri(self, x0, y0, x1, y1, x2, y2, c):
        pts = sorted([(x0, y0), (x1, y1), (x2, y2)], key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts

        def edge_x(y, px0, py0, px1, py1):
            if py1 == py0:
                return px0
            return px0 + (px1 - px0) * (y - py0) / (py1 - py0)

        for y in range(ay, cy + 1):
            if y < by:
                xa = edge_x(y, ax, ay, bx, by)
                xb = edge_x(y, ax, ay, cx, cy)
            else:
                xa = edge_x(y, bx, by, cx, cy)
                xb = edge_x(y, ax, ay, cx, cy)
            xa, xb = int(min(xa, xb)), int(max(xa, xb))
            self.rect(xa, y, xb - xa + 1, 1, c)

    def text(self, x, y, s, scale, c):
        cx = x
        for ch in s:
            glyph = FONT.get(ch)
            if glyph is None:
                glyph = FONT[" "]
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, c)
            cx += 6 * scale
        return cx

    def para(self, x, y, max_w, s, scale, c, gap=6):
        for line in wrap(s, max_w, scale):
            self.text(x, y, line, scale, c)
            y += 7 * scale + gap
        return y

    def border(self, thickness, c):
        for t in range(thickness):
            self.rect(8 + t, 8 + t, W - 16 - 2 * t, 1, c)
            self.rect(8 + t, H - 9 - t, W - 16 - 2 * t, 1, c)
            self.rect(8 + t, 8 + t, 1, H - 16 - 2 * t, c)
            self.rect(W - 9 - t, 8 + t, 1, H - 16 - 2 * t, c)


def flag_china(cv, x, y, w, h):
    cv.rect(x, y, w, h, RED)
    cv.disc(x + w // 5, y + h // 3, h // 5, (255, 220, 60))


def flag_russia(cv, x, y, w, h):
    cv.rect(x, y, w, h // 3, WHITE)
    cv.rect(x, y + h // 3, w, h // 3, BLUE)
    cv.rect(x, y + 2 * h // 3, w, h - 2 * h // 3, RED)


def flag_usa(cv, x, y, w, h):
    for i in range(7):
        cv.rect(x, y + i * h // 7, w, h // 7 + 1,
                RED if i % 2 == 0 else WHITE)
    cv.rect(x, y, w * 2 // 5, h * 4 // 7, NAVY)


def draw_lead_scene(cv, x0, y0, w, h):
    # Sky and sea.
    cv.rect(x0, y0, w, h * 3 // 5, SKY)
    cv.rect(x0, y0 + h * 3 // 5, w, h - h * 3 // 5, SEA)
    # Smoke from the burning bow.
    cv.disc(x0 + w - 70, y0 + 120, 13, GREY)
    cv.disc(x0 + w - 52, y0 + 100, 17, GREY)
    cv.disc(x0 + w - 74, y0 + 82, 11, GREY)
    # Fireball over the bow.
    cv.disc(x0 + w - 56, y0 + 158, 26, EMBER)
    cv.disc(x0 + w - 56, y0 + 150, 17, FIRE)
    cv.disc(x0 + w - 56, y0 + 144, 9, FLAME)
    cv.tri(x0 + w - 84, y0 + 158, x0 + w - 56, y0 + 118,
           x0 + w - 30, y0 + 158, FIRE)
    # Drone above, watching.
    cv.disc(x0 + 150, y0 + 56, 5, INK)
    cv.line(x0 + 132, y0 + 56, x0 + 168, y0 + 56, INK, 3)
    cv.line(x0 + 150, y0 + 56, x0 + 162, y0 + 70, INK, 2)
    # Tanker hull straddling the waterline.
    cv.rect(x0 + 36, y0 + 188, 280, 36, (28, 28, 28))
    cv.rect(x0 + 60, y0 + 160, 64, 28, WHITE)
    cv.rect(x0 + 80, y0 + 144, 26, 16, RED)
    cv.line(x0 + 124, y0 + 160, x0 + 124, y0 + 134, INK, 3)
    # White wave dashes on the sea.
    for wx in (x0 + 16, x0 + 96, x0 + 176, x0 + 256, x0 + 316):
        cv.rect(wx, y0 + h - 84, 34, 3, WHITE)
        cv.rect(wx + 20, y0 + h - 52, 34, 3, WHITE)
        cv.rect(wx, y0 + h - 20, 34, 3, WHITE)


def draw_bridge(cv, x0, y0, w, h):
    # Water at the bottom.
    cv.rect(x0, y0 + h - 36, w, 36, SEA)
    # Two towers with small caps.
    cv.rect(x0 + 14, y0 + 20, 10, 76, INK)
    cv.rect(x0 + 10, y0 + 14, 18, 6, INK)
    cv.rect(x0 + w - 24, y0 + 20, 10, 76, INK)
    cv.rect(x0 + w - 28, y0 + 14, 18, 6, INK)
    # Deck in two pieces with a clear gap where the span fell.
    cv.rect(x0, y0 + 52, 60, 8, INK)
    cv.rect(x0 + w - 60, y0 + 52, 60, 8, INK)
    # Fallen span, angled down into the water in the gap.
    cv.line(x0 + 64, y0 + 60, x0 + 92, y0 + h - 40, INK, 5)
    cv.disc(x0 + 94, y0 + h - 38, 4, WHITE)


def draw_page(cv):
    cv.border(4, INK)

    # Masthead.
    title = "THE WORLD TODAY"
    tx = (W - text_width(title, 9)) // 2
    cv.text(tx, 28, title, 9, INK)
    cv.rect(28, 100, 968, 3, INK)
    cv.rect(28, 107, 968, 1, INK)

    # Red date band.
    cv.rect(28, 118, 968, 52, RED)
    date = "TUESDAY 17 NOVEMBER 2026"
    dx = (W - text_width(date, 5)) // 2
    cv.text(dx, 126, date, 5, WHITE)

    # Lead story: US-Iran escalation.
    cv.text(28, 186, "US-IRAN WAR ESCALATES", 3, RED)
    cv.text(28, 216, "FOURTH TANKER HIT", 5, INK)
    cv.text(28, 259, "US DRONE SEIZED", 5, INK)
    cv.para(28, 308, 592,
            "A FOURTH OIL TANKER CAUGHT FIRE IN THE STRAIT OF HORMUZ "
            "AFTER STRIKING A NAVAL MINE. IRAN'S REVOLUTIONARY GUARDS "
            "SAID THEY SEIZED A US MQ-170 DRONE NEAR QESHM ISLAND. "
            "IRANIAN DRONES TARGETED A US RADAR SYSTEM AT BAHRAIN'S "
            "SHEIKH ISA AIR BASE. TRUMP THREATENED TO KEEP A NAVAL "
            "BLOCKADE OF IRAN.",
            2, INK)
    draw_lead_scene(cv, 640, 186, 356, 362)

    # Divider.
    cv.rect(28, 560, 968, 3, INK)

    # Second row: Kerch Bridge and the Shenzhen summit.
    cv.text(28, 574, "KERCH BRIDGE", 4, INK)
    cv.text(28, 608, "STRUCK", 4, INK)
    cv.para(28, 648, 300,
            "UKRAINE HIT THE BRIDGE TO CRIMEA WITH MISSILES AND "
            "DRONES. PART OF IT COLLAPSED. RUSSIA STRUCK BRIDGES "
            "IN KYIV IN RETURN.",
            2, INK)
    draw_bridge(cv, 340, 648, 160, 132)
    cv.text(524, 574, "SUMMIT IN", 4, INK)
    cv.text(524, 608, "SHENZHEN", 4, INK)
    cv.para(524, 648, 300,
            "XI, TRUMP AND PUTIN MEET ON THURSDAY IN SHENZHEN. "
            "THE FIRST TRILATERAL SUMMIT.",
            2, INK)
    flag_china(cv, 524, 740, 140, 34)
    flag_russia(cv, 676, 740, 140, 34)
    flag_usa(cv, 828, 740, 140, 34)

    # Divider.
    cv.rect(28, 794, 968, 3, INK)

    # Third row: three short stories with coloured top rules.
    cv.rect(28, 800, 302, 6, RED)
    cv.rect(362, 800, 302, 6, NAVY)
    cv.rect(696, 800, 300, 6, GREEN)
    cv.text(28, 814, "GAZA WINTER", 3, INK)
    cv.text(28, 841, "CRISIS", 3, INK)
    cv.text(362, 814, "COP31 DEAL", 3, INK)
    cv.text(362, 841, "IN ANTALYA", 3, INK)
    cv.text(696, 814, "MEASLES STATUS", 3, INK)
    cv.text(696, 841, "LOST", 3, INK)
    cv.para(28, 874, 302,
            "1.7M REMAIN DISPLACED. 1.4M FACE ACUTE HUNGER AS "
            "WINTER SETS IN.",
            2, INK)
    cv.para(362, 874, 302,
            "FASTER FOSSIL-FUEL PHASE-OUT, $120B A YEAR FOR "
            "ADAPTATION BY 2035.",
            2, INK)
    cv.para(696, 874, 300,
            "US LOSES ELIMINATION STATUS AFTER 26 YEARS. 5,400+ "
            "CASES, 10 DEATHS.",
            2, INK)

    # Divider and the day's briefs.
    cv.rect(28, 940, 968, 3, INK)
    cv.para(28, 950, 968,
            "ALSO TODAY: ZAPORIZHZHIA STRIKE KILLS 40 - SCHOOL AID "
            "CENTRE KILLS 26 - KEMEROVO PLANE CRASH KILLS 19 - JAPAN "
            "SCRAMBLED JETS - MOLDOVA SHUT AIRSPACE - HOUTHIS ADVANCE "
            "IN YEMEN - 146,000 PROTEST IN FRANCE - INDIA WIN U-19 "
            "ASIA CUP",
            2, INK)


def chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return out


def write_png(path, cv):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw.extend(cv.px[y * W * 3:(y + 1) * W * 3])
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = Canvas()
    draw_page(cv)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, cv)
    print("wrote %s (%d bytes, %dx%d)" % (path, size, W, H))


if __name__ == "__main__":
    main()
