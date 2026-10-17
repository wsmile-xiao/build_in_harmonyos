#!/usr/bin/env python3
"""Functional pygame probe shared by Conan and HarmonyOS device validation."""

import argparse
import importlib
import importlib.metadata
import io
import sys
import traceback
from pathlib import Path


class Probe:
    def __init__(self):
        self.count = 0

    def step(self, number, purpose, command):
        print(f"[STEP] {number}: {purpose}; command={command}", flush=True)

    def check(self, name, condition, expected, actual):
        self.count += 1
        if not condition:
            print(
                f"[FAIL] assertion={self.count} name={name} "
                f"expected={expected!r} actual={actual!r}",
                file=sys.stderr,
                flush=True,
            )
            raise AssertionError(name)
        print(
            f"[PASS] assertion={self.count} name={name} actual={actual!r}",
            flush=True,
        )


def run(work_dir, self_test_failure=False):
    probe = Probe()
    probe.step(
        1,
        "import packaged native modules",
        "import pygame and required extensions",
    )
    import pygame

    required_modules = (
        "pygame.base",
        "pygame.surface",
        "pygame.display",
        "pygame.draw",
        "pygame.imageext",
        "pygame.font",
        "pygame.mixer",
        "pygame.gfxdraw",
        "pygame.freetype",
        "pygame._sdl2.video",
    )
    imported = [importlib.import_module(name).__name__ for name in required_modules]
    base_path = Path(importlib.import_module("pygame.base").__file__)
    probe.check(
        "pygame-version", pygame.version.ver == "2.6.1", "2.6.1", pygame.version.ver
    )
    sdl_version = pygame.get_sdl_version()
    probe.check(
        "sdl-version", sdl_version >= (2, 0, 12), ">= (2, 0, 12)", sdl_version
    )
    probe.check(
        "native-base-extension",
        base_path.suffix in (".so", ".pyd"),
        ".so/.pyd",
        base_path,
    )
    probe.check(
        "required-modules",
        len(imported) == len(required_modules),
        len(required_modules),
        imported,
    )

    width, height = 64, 48

    probe.step(
        2,
        "initialize SDL video and event subsystems",
        "pygame.display.init and create window",
    )
    pygame.display.init()
    screen = pygame.display.set_mode((width, height))
    display_size = screen.get_size()
    driver_name = pygame.display.get_driver()
    probe.check(
        "display-initialized",
        pygame.display.get_init(),
        True,
        pygame.display.get_init(),
    )
    probe.check(
        "display-size", display_size == (width, height), (width, height), display_size
    )
    probe.check("video-driver", driver_name == "dummy", "dummy", driver_name)
    event_type = pygame.event.custom_type()
    pygame.event.post(pygame.event.Event(event_type, payload="ohos"))
    matching = [event for event in pygame.event.get() if event.type == event_type]
    probe.check(
        "event-round-trip",
        len(matching) == 1 and matching[0].payload == "ohos",
        "one event",
        matching,
    )

    probe.step(
        3,
        "draw, transform, and present pixels",
        "Surface.fill/draw/smoothscale/present",
    )
    surface = pygame.Surface((32, 24), pygame.SRCALPHA, 32)
    surface.fill((10, 20, 30, 255))
    pygame.draw.rect(surface, (220, 40, 30, 255), (4, 4, 8, 6))
    probe.check(
        "surface-size", surface.get_size() == (32, 24), (32, 24), surface.get_size()
    )
    probe.check(
        "background-pixel",
        surface.get_at((1, 1)) == (10, 20, 30, 255),
        (10, 20, 30, 255),
        surface.get_at((1, 1)),
    )
    probe.check(
        "drawn-pixel",
        surface.get_at((5, 5)) == (220, 40, 30, 255),
        (220, 40, 30, 255),
        surface.get_at((5, 5)),
    )
    probe.check(
        "outside-rect-pixel",
        surface.get_at((20, 15)) == (10, 20, 30, 255),
        (10, 20, 30, 255),
        surface.get_at((20, 15)),
    )
    scaled = pygame.transform.smoothscale(surface, (width, height))
    probe.check(
        "transformed-size",
        scaled.get_size() == (width, height),
        (width, height),
        scaled.get_size(),
    )
    blit_rect = screen.blit(scaled, (0, 0))
    pygame.display.flip()
    presented_pixel = screen.get_at((10, 10))
    probe.check(
        "present-rect",
        blit_rect.size == (width, height),
        (width, height),
        blit_rect.size,
    )
    probe.check(
        "presented-pixel",
        presented_pixel[:3] == (220, 40, 30),
        (220, 40, 30),
        presented_pixel,
    )

    probe.step(
        4,
        "exercise SDL_image and PNG error handling",
        "pygame.image.save/load",
    )
    image_version = pygame.image.get_sdl_image_version()
    probe.check(
        "sdl-image-version", image_version is not None, "version tuple", image_version
    )
    png_path = work_dir / "pygame-probe.png"
    pygame.image.save(surface, png_path)
    probe.check(
        "png-created",
        png_path.is_file() and png_path.stat().st_size > 32,
        "non-empty PNG",
        png_path.stat().st_size if png_path.exists() else 0,
    )
    loaded = pygame.image.load(png_path)
    probe.check(
        "png-size",
        loaded.get_size() == surface.get_size(),
        surface.get_size(),
        loaded.get_size(),
    )
    probe.check(
        "png-pixel",
        loaded.get_at((5, 5))[:3] == (220, 40, 30),
        (220, 40, 30),
        loaded.get_at((5, 5)),
    )
    invalid_raised = False
    try:
        pygame.image.load(io.BytesIO(b"not-an-image"), "invalid.png")
    except pygame.error:
        invalid_raised = True
    probe.check("invalid-image-error", invalid_raised, True, invalid_raised)

    probe.step(5, "render bundled font", "pygame.font.Font.render")
    pygame.font.init()
    probe.check(
        "font-initialized", pygame.font.get_init(), True, pygame.font.get_init()
    )
    ttf_version = pygame.font.get_sdl_ttf_version()
    probe.check(
        "sdl-ttf-version", ttf_version >= (2, 0, 15), ">= (2, 0, 15)", ttf_version
    )
    rendered = pygame.font.Font(None, 20).render(
        "HarmonyOS", True, (250, 250, 250)
    )
    probe.check(
        "font-render-size",
        rendered.get_width() > 0 and rendered.get_height() > 0,
        "positive dimensions",
        rendered.get_size(),
    )
    bounds = rendered.get_bounding_rect()
    probe.check(
        "font-render-bounds",
        bounds.width > 0 and bounds.height > 0,
        "positive bounds",
        bounds,
    )
    freetype_version = pygame.freetype.get_version()
    probe.check(
        "freetype-version",
        freetype_version >= (2, 0, 0),
        ">= (2, 0, 0)",
        freetype_version,
    )

    probe.step(
        6,
        "exercise SDL_mixer with an in-memory sample",
        "pygame.mixer.Sound",
    )
    if pygame.mixer.get_init():
        pygame.mixer.quit()
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    mixer_init = pygame.mixer.get_init()
    probe.check("mixer-initialized", mixer_init is not None, "format tuple", mixer_init)
    mixer_version = pygame.mixer.get_sdl_mixer_version()
    probe.check(
        "sdl-mixer-version",
        mixer_version >= (2, 0, 4),
        ">= (2, 0, 4)",
        mixer_version,
    )
    raw = b"\x00\x00" * 2205
    sound = pygame.mixer.Sound(buffer=raw)
    probe.check(
        "sound-buffer", len(sound.get_raw()) == len(raw), len(raw), len(sound.get_raw())
    )
    length = sound.get_length()
    probe.check("sound-length", 0.09 <= length <= 0.11, "0.09..0.11 seconds", length)
    channel = sound.play()
    probe.check("sound-play", channel is not None, "Channel", channel)
    sound.stop()

    queued_sound = pygame.mixer.Sound(buffer=raw * 20)
    channel.play(sound, loops=-1)
    channel.queue(queued_sound)
    queued = channel.get_queue()
    probe.check("sound-queued", queued is queued_sound, queued_sound, queued)
    channel.stop()
    busy_after_stop = channel.get_busy()
    queued_after_stop = channel.get_queue()
    probe.check("channel-stop-immediate", not busy_after_stop, False, busy_after_stop)
    probe.check("channel-stop-clears-queue", queued_after_stop is None, None, queued_after_stop)

    probe.step(7, "verify installed metadata", "importlib.metadata.version")
    metadata_version = importlib.metadata.version("pygame")
    probe.check(
        "distribution-metadata", metadata_version == "2.6.1", "2.6.1", metadata_version
    )

    expected = 34
    if probe.count != expected:
        raise AssertionError(
            f"internal assertion count mismatch: {probe.count} != {expected}"
        )
    if self_test_failure:
        probe.step(
            8,
            "prove that a failed assertion returns nonzero",
            "intentional negative control",
        )
        probe.check("negative-control", False, True, False)
    print(
        f"[PASS] summary assertions={probe.count}/{expected} "
        f"video_driver={driver_name} headless_mode=True",
        flush=True,
    )
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--self-test-failure", action="store_true")
    args = parser.parse_args()
    work_dir = Path(args.work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        return run(work_dir, self_test_failure=args.self_test_failure)
    except Exception as exc:
        print(f"[FAIL] exception={type(exc).__name__} detail={exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1
    finally:
        try:
            import pygame

            pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
