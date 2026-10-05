#!/usr/bin/env python3
"""Proustite Prism — ruby-silver refractor arcade for ElbowOS. Python 3 + pygame.

Rotate a hexagonal prism so the exit beam kisses a matching gem.
Left/Right or A/D rotate. Space pulses a wider catch. R restarts.
"""
import math
import os
import random
import subprocess
import sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/workspace/artifacts/PROUSTITE_PRISM_ElbowOS.mp4")
TITLE, HANDLE = "PROUSTITE PRISM", "x.com/ElbowOS"
INK = (14, 4, 8)
WINE = (62, 12, 24)
RUBY = (255, 58, 78)
AMBER = (255, 186, 64)
SILVER = (214, 222, 236)
CREAM = (255, 238, 228)
VIOLET = (186, 104, 214)
COLS = (RUBY, AMBER, VIOLET)
NAMES = ("RUBY", "AMBER", "VIOLET")
CX, CY, PR = 540, 980, 148


def wrap(a):
    while a > math.pi:
        a -= math.tau
    while a < -math.pi:
        a += math.tau
    return a


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY and not RECORD else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            self.screen = pygame.Surface((W, H))
        pygame.display.set_caption(TITLE)
        self.font = pygame.font.SysFont("dejavusans", 64, bold=True)
        self.mid = pygame.font.SysFont("dejavusans", 42, bold=True)
        self.small = pygame.font.SysFont("dejavusans", 32, bold=True)
        self.bg = self._bg()
        self.reset()

    def _bg(self):
        surf = pygame.Surface((W, H))
        for y in range(H):
            t = y / H
            c = (int(28 - 16 * t), int(6 + 4 * math.sin(t * 3)), int(12 + 10 * t))
            pygame.draw.line(surf, c, (0, y), (W, y))
        for i in range(8):
            x = 80 + i * 130
            pygame.draw.line(surf, (48, 14, 26), (x, 180), (x + 40, H - 80), 2)
        pygame.draw.circle(surf, (40, 10, 18), (CX, CY), 520, 3)
        return surf

    def reset(self):
        self.ang = 0.4
        self.spin = 0.0
        self.col = 0
        self.score = 0
        self.streak = 0
        self.flash = 0
        self.pulse = 0
        self.pops = []
        self.bits = []
        self.gems = []
        for i in range(7):
            self.gems.append(self._gem(i * math.tau / 7 + 0.3))
        self.t = 0.0

    def _gem(self, ang):
        return {"ang": ang, "col": random.randrange(3), "rad": random.choice((390, 460, 530)), "hit": 0}

    def update(self, dt, keys, auto):
        self.t += dt
        self.flash = max(0, self.flash - dt)
        self.pulse = max(0, self.pulse - dt)
        if auto:
            want = None
            best = 9
            for g in self.gems:
                if g["col"] != self.col or g["hit"] > 0:
                    continue
                d = abs(wrap(g["ang"] - self.ang))
                if d < best:
                    best, want = d, g["ang"]
            if want is None:
                self.spin = 0.9
            else:
                err = wrap(want - self.ang)
                self.spin = max(-2.6, min(2.6, err * 4.2))
                if abs(err) < 0.12:
                    self.pulse = 0.18
        else:
            self.spin = 0.0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.spin = -2.4
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.spin = 2.4
        self.ang = wrap(self.ang + self.spin * dt)
        for g in self.gems:
            g["ang"] = wrap(g["ang"] + dt * (0.22 + 0.05 * (g["rad"] % 3)))
            g["hit"] = max(0, g["hit"] - dt)
            if abs(wrap(g["ang"] - self.ang)) < (0.20 if self.pulse else 0.11) and g["hit"] <= 0:
                gx, gy = self.gpos(g)
                if g["col"] == self.col:
                    self.streak += 1
                    gain = 10 + self.streak * 2
                    self.score += gain
                    g["hit"] = 0.85
                    g["col"] = random.randrange(3)
                    g["ang"] = wrap(self.ang + random.choice((-1, 1)) * random.uniform(1.2, 2.4))
                    self.pops.append([gx, gy, gain, 0.7])
                    self.burst(gx, gy, COLS[self.col])
                    if self.streak % 4 == 0:
                        self.col = (self.col + 1) % 3
                else:
                    self.streak = 0
                    self.flash = 0.25
                    g["hit"] = 0.45
                    self.burst(gx, gy, (255, 220, 220))
        self.pops = [[x, y - 40 * dt, n, life - dt] for x, y, n, life in self.pops if life > dt]
        nxt = []
        for b in self.bits:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            b[4] -= dt
            if b[4] > 0:
                nxt.append(b)
        self.bits = nxt

    def gpos(self, g):
        return CX + math.cos(g["ang"]) * g["rad"], CY + math.sin(g["ang"]) * g["rad"]

    def burst(self, x, y, col):
        for _ in range(10):
            a = random.random() * math.tau
            s = random.uniform(80, 280)
            self.bits.append([x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(0.25, 0.55), col])

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        if self.flash:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((255, 40, 60, int(90 * self.flash / 0.25)))
            surf.blit(veil, (0, 0))
        beam = COLS[self.col]
        ex = CX + math.cos(self.ang) * 620
        ey = CY + math.sin(self.ang) * 620
        wide = 26 if self.pulse else 14
        for w, a in ((wide + 22, 40), (wide + 8, 90), (wide, 210)):
            glow = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.line(glow, (*beam, a), (CX, 250), (CX, CY), w)
            pygame.draw.line(glow, (*beam, a), (CX, CY), (ex, ey), w)
            surf.blit(glow, (0, 0))
        pygame.draw.circle(surf, beam, (CX, 230), 28)
        pygame.draw.circle(surf, CREAM, (CX, 230), 10)
        pts = []
        for i in range(6):
            a = self.ang + i * math.tau / 6
            pts.append((CX + math.cos(a) * PR, CY + math.sin(a) * PR))
        pygame.draw.polygon(surf, (86, 18, 32), pts)
        pygame.draw.polygon(surf, SILVER, pts, 6)
        inner = []
        for i in range(6):
            a = -self.ang + i * math.tau / 6
            inner.append((CX + math.cos(a) * 62, CY + math.sin(a) * 62))
        pygame.draw.polygon(surf, beam, inner)
        pygame.draw.circle(surf, CREAM, (CX, CY), 16)
        for g in self.gems:
            x, y = self.gpos(g)
            c = COLS[g["col"]]
            if g["hit"]:
                c = tuple(min(255, v + 80) for v in c)
            diamond = [(x, y - 28), (x + 22, y), (x, y + 28), (x - 22, y)]
            pygame.draw.polygon(surf, c, diamond)
            pygame.draw.polygon(surf, CREAM, diamond, 2)
        for x, y, vx, vy, life, col in self.bits:
            pygame.draw.circle(surf, col, (int(x), int(y)), max(2, int(6 * life / 0.5)))
        for x, y, n, life in self.pops:
            pop = self.small.render(f"+{n}", True, AMBER)
            surf.blit(pop, pop.get_rect(center=(int(x), int(y))))
        banner = pygame.Surface((W, 150), pygame.SRCALPHA)
        banner.fill((18, 4, 8, 170))
        surf.blit(banner, (0, 36))
        title = self.font.render(TITLE, True, CREAM)
        surf.blit(title, title.get_rect(center=(W // 2, 92)))
        tag = self.small.render(NAMES[self.col] + " BEAM", True, beam)
        surf.blit(tag, tag.get_rect(center=(W // 2, 210)))
        foot = pygame.Surface((W, 170), pygame.SRCALPHA)
        foot.fill((18, 4, 8, 180))
        surf.blit(foot, (0, H - 190))
        sc = self.mid.render(f"SCORE  {self.score}", True, AMBER)
        surf.blit(sc, sc.get_rect(center=(W // 2, H - 130)))
        st = self.small.render(f"STREAK  {self.streak}", True, SILVER)
        surf.blit(st, st.get_rect(center=(W // 2, H - 78)))
        handle = self.small.render(HANDLE, True, RUBY)
        surf.blit(handle, handle.get_rect(center=(W // 2, H - 34)))

    def record(self):
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
            "-preset", "veryfast", "-movflags", "+faststart", OUT,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        frames = FPS * SECS
        dt = 1 / FPS
        try:
            for _ in range(frames):
                self.update(dt, None, True)
                self.draw(self.screen)
                proc.stdin.write(pygame.image.tobytes(self.screen, "RGB"))
        finally:
            proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "ignore")
        rc = proc.wait()
        if rc != 0 or not os.path.isfile(OUT) or os.path.getsize(OUT) < 10000:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1500:]}")
        print("wrote", OUT, os.path.getsize(OUT))
        pygame.quit()

    def play(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            dt = min(0.05, clock.tick(FPS) / 1000)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        running = False
                    elif ev.key == pygame.K_r:
                        self.reset()
                    elif ev.key == pygame.K_SPACE:
                        self.pulse = 0.22
            keys = pygame.key.get_pressed()
            self.update(dt, keys, False)
            self.draw(self.screen)
            pygame.display.flip()
        pygame.quit()


def main():
    g = Game()
    if PLAY and not RECORD:
        g.play()
    else:
        g.record()


if __name__ == "__main__":
    main()
