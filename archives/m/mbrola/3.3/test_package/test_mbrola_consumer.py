#!/usr/bin/env python3
"""Semantic consumer validation for the packaged MBROLA executable.

The suite drives the installed ``mbrola`` binary end to end against the
published ``mbrola-gr2`` voice database:

* CLI contract: banner, usage, option validation and fatal error exits.
* Database inspection with ``-i``.
* Real synthesis of the upstream GR2 example (211 phoneme commands):
  WAV/AU/RAW output, duration against the score, amplitude, determinism.
* Runtime options: time ratio, volume ratio, frequency ratio, voice freq.
* ROM round trip (``-W`` dump + ``-w`` render) byte-identical to a direct
  render, mirroring the upstream Makefile ``check`` target.
* Negative controls: unknown phoneme without/with ``-e``, missing database
  or score, invalid volume ratio.

Usage:
    test_mbrola_consumer.py <mbrola-binary> <mbrola-gr2-root> <workdir>
"""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

GR2_VOICE_REL = os.path.join("share", "mbrola", "gr2", "gr2")
GR2_PHO_REL = os.path.join("share", "mbrola", "gr2", "TEST", "DEMOST~1.PHO")
EXPECTED_PHO_COMMANDS = 211
EXPECTED_PHO_MS = 17264.0
SAMPLE_RATE = 22050


class Checks:
    def __init__(self, scenario):
        self.scenario = scenario
        self.count = 0

    def require(self, condition, message):
        if not condition:
            raise AssertionError("[{}] {}".format(self.scenario, message))
        self.count += 1


def run(mbrola, args):
    proc = subprocess.run(
        [str(mbrola)] + [str(arg) for arg in args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc.returncode, proc.stdout.decode("latin-1")


def read_wav(path):
    payload = Path(path).read_bytes()
    if payload[:4] != b"RIFF" or payload[8:12] != b"WAVE":
        raise AssertionError("not a RIFF/WAVE file: {}".format(path))
    pos = 12
    fmt = None
    data = None
    while pos + 8 <= len(payload):
        chunk_id = payload[pos:pos + 4]
        size = struct.unpack_from("<I", payload, pos + 4)[0]
        if chunk_id == b"fmt ":
            fmt = struct.unpack_from("<HHIIHH", payload, pos + 8)
        elif chunk_id == b"data":
            data = payload[pos + 8:pos + 8 + size]
        pos += 8 + size + (size & 1)
    if fmt is None or data is None:
        raise AssertionError("missing fmt/data chunk in {}".format(path))
    return payload, fmt, data


def samples_of(data):
    count = len(data) // 2
    return struct.unpack("<%dh" % count, data[:count * 2])


def rms(values):
    return math.sqrt(sum(value * value for value in values) / len(values))


def parse_pho(path):
    text = Path(path).read_bytes().replace(b"\x00", b"").decode("latin-1")
    durations = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        fields = line.split()
        durations.append(float(fields[1]))
    return durations


def scenario_fixtures(checks, ctx):
    checks.require(Path(ctx["mbrola"]).is_file(), "mbrola executable not installed")
    # HMDFS normalizes permission bits, so only require a non-empty binary here;
    # actual executability is proven by every later subprocess call.
    checks.require(Path(ctx["mbrola"]).stat().st_size > 0, "mbrola executable is empty")
    checks.require(ctx["db"].is_file(), "mbrola-gr2 database not installed")
    checks.require(ctx["pho"].is_file(), "upstream GR2 example score not installed")
    checks.require(
        len(ctx["pho_durations"]) == EXPECTED_PHO_COMMANDS,
        "unexpected GR2 example command count: {}".format(len(ctx["pho_durations"])),
    )


def scenario_cli_contract(checks, ctx):
    code, out = run(ctx["mbrola"], [])
    checks.require(code == 0, "bare mbrola exited {}".format(code))
    checks.require("MBROLA" in out, "banner does not name MBROLA")
    checks.require("speech synthesizer" in out, "banner does not describe the program")
    checks.require("For help type" in out, "banner misses the help hint")

    code, out = run(ctx["mbrola"], ["-h"])
    checks.require(code == 0, "mbrola -h exited {}".format(code))
    checks.require("USAGE:" in out, "usage banner is missing")
    checks.require(
        "database pho_file+ output_file" in out,
        "usage signature changed: {!r}".format(out[:200]),
    )
    options = ["-i", "-e", "-c", "-F", "-v", "-f", "-t", "-l", "-R", "-C", "-I", "-W", "-w"]
    checks.require(
        sum(1 for option in options if option in out) >= 12,
        "usage does not document the expected option set",
    )

    code, out = run(ctx["mbrola"], ["-Z", ctx["db"], ctx["pho"], ctx["work"] / "bad-option.wav"])
    checks.require(code != 0, "unknown option was accepted (exit {})".format(code))
    checks.require("not recognized" in out, "unknown option message missing: {!r}".format(out[:200]))

    code, out = run(
        ctx["mbrola"],
        [ctx["work"] / "no-such-database", ctx["pho"], ctx["work"] / "no-db.wav"],
    )
    checks.require(code != 0, "missing database was accepted (exit {})".format(code))
    checks.require("cannot find file" in out, "missing database message missing: {!r}".format(out[:200]))

    code, out = run(
        ctx["mbrola"],
        [ctx["db"], ctx["work"] / "no-such-score.pho", ctx["work"] / "no-score.wav"],
    )
    checks.require(code != 0, "missing score was accepted (exit {})".format(code))
    checks.require("input file" in out, "missing score message missing: {!r}".format(out[:200]))

    code, out = run(
        ctx["mbrola"],
        ["-v", "0", ctx["db"], ctx["pho"], ctx["work"] / "zero-volume.wav"],
    )
    checks.require(code != 0, "volume ratio 0 was accepted (exit {})".format(code))
    checks.require("volume ratio" in out, "volume validation message missing: {!r}".format(out[:200]))


def scenario_database_info(checks, ctx):
    code, out = run(ctx["mbrola"], ["-i", ctx["db"]])
    checks.require(code == 0, "mbrola -i exited {}".format(code))
    checks.require("GR2 male Hellenic(Greek) voice" in out, "voice identity missing from -i output")
    checks.require("release May2001" in out, "voice release missing from -i output")
    checks.require("SAMPA" in out, "phoneme alphabet header missing from -i output")
    checks.require("(silence)" in out, "silence phoneme row missing from -i output")


def scenario_real_synthesis(checks, ctx):
    base = ctx["work"] / "direct.wav"
    code, out = run(ctx["mbrola"], [ctx["db"], ctx["pho"], base])
    checks.require(code == 0, "synthesis exited {} ({!r})".format(code, out[:200]))

    payload, fmt, data = read_wav(base)
    checks.require(fmt[0] == 1, "expected linear PCM, got format tag {}".format(fmt[0]))
    checks.require(fmt[1] == 1, "expected mono output, got {} channels".format(fmt[1]))
    checks.require(fmt[2] == SAMPLE_RATE, "expected {} Hz, got {}".format(SAMPLE_RATE, fmt[2]))
    checks.require(fmt[5] == 16, "expected 16 bit samples, got {}".format(fmt[5]))
    checks.require(
        len(payload) == 44 + len(data),
        "unexpected RIFF layout: file={} data={}".format(len(payload), len(data)),
    )

    duration = len(data) / 2.0 / SAMPLE_RATE
    expected = ctx["pho_ms"] / 1000.0
    checks.require(
        abs(duration - expected) < 0.1,
        "rendered {:.3f}s but the score asks for {:.3f}s".format(duration, expected),
    )

    values = samples_of(data)
    checks.require(max(abs(value) for value in values) > 1000, "synthesis is effectively silent")
    checks.require(rms(values) > 100.0, "synthesis RMS is implausibly low")
    checks.require(
        any(value > 0 for value in values) and any(value < 0 for value in values),
        "synthesis is not a bipolar waveform",
    )

    again = ctx["work"] / "direct-again.wav"
    code, out = run(ctx["mbrola"], [ctx["db"], ctx["pho"], again])
    checks.require(code == 0, "re-synthesis exited {}".format(code))
    checks.require(base.read_bytes() == again.read_bytes(), "synthesis is not deterministic")

    ctx["base_data"] = data
    ctx["base_duration"] = duration
    ctx["base_rms"] = rms(values)


def scenario_runtime_options(checks, ctx):
    slow = ctx["work"] / "time-2.wav"
    code, out = run(ctx["mbrola"], ["-t", "2.0", ctx["db"], ctx["pho"], slow])
    checks.require(code == 0, "-t 2.0 exited {} ({!r})".format(code, out[:200]))
    _, _, data = read_wav(slow)
    ratio = (len(data) / 2.0 / SAMPLE_RATE) / ctx["base_duration"]
    checks.require(abs(ratio - 2.0) < 0.02, "time ratio {:.4f} differs from 2.0".format(ratio))

    quiet = ctx["work"] / "volume-half.wav"
    code, out = run(ctx["mbrola"], ["-v", "0.5", ctx["db"], ctx["pho"], quiet])
    checks.require(code == 0, "-v 0.5 exited {} ({!r})".format(code, out[:200]))
    _, _, data = read_wav(quiet)
    checks.require(len(data) == len(ctx["base_data"]), "volume ratio changed the sample count")
    quiet_rms = rms(samples_of(data))
    ratio = quiet_rms / ctx["base_rms"]
    checks.require(abs(ratio - 0.5) < 0.02, "volume 0.5 RMS ratio is {:.4f}".format(ratio))

    high = ctx["work"] / "freq-2.wav"
    code, out = run(ctx["mbrola"], ["-f", "2.0", ctx["db"], ctx["pho"], high])
    checks.require(code == 0, "-f 2.0 exited {} ({!r})".format(code, out[:200]))
    _, _, data = read_wav(high)
    checks.require(
        abs(len(data) - len(ctx["base_data"])) <= 100,
        "frequency ratio changed the sample count too much",
    )
    checks.require(data != ctx["base_data"], "frequency ratio 2.0 produced identical samples")

    child = ctx["work"] / "voice-14k.wav"
    code, out = run(ctx["mbrola"], ["-l", "14000", ctx["db"], ctx["pho"], child])
    checks.require(code == 0, "-l 14000 exited {} ({!r})".format(code, out[:200]))
    _, _, data = read_wav(child)
    ratio = (len(data) / 2.0 / SAMPLE_RATE) / ctx["base_duration"]
    expected = 14000.0 / SAMPLE_RATE
    checks.require(
        abs(ratio - expected) < 0.01,
        "voice ratio {:.4f} differs from {:.4f}".format(ratio, expected),
    )


def scenario_output_formats(checks, ctx):
    au = ctx["work"] / "direct.au"
    code, out = run(ctx["mbrola"], [ctx["db"], ctx["pho"], au])
    checks.require(code == 0, "au synthesis exited {} ({!r})".format(code, out[:200]))
    payload = au.read_bytes()
    checks.require(payload[:4] == b".snd", "au magic is missing")
    data_offset, data_size, encoding, rate, channels = struct.unpack_from(">IIIII", payload, 4)
    checks.require(data_offset == 28, "unexpected au data offset {}".format(data_offset))
    checks.require(
        data_size == len(ctx["base_data"]),
        "au data size {} differs from wav data size {}".format(data_size, len(ctx["base_data"])),
    )
    checks.require(encoding == 3, "unexpected au encoding {}".format(encoding))
    checks.require(rate == SAMPLE_RATE, "unexpected au sample rate {}".format(rate))
    checks.require(channels == 1, "unexpected au channel count {}".format(channels))

    raw = ctx["work"] / "direct.raw"
    code, out = run(ctx["mbrola"], [ctx["db"], ctx["pho"], raw])
    checks.require(code == 0, "raw synthesis exited {} ({!r})".format(code, out[:200]))
    checks.require(
        raw.stat().st_size == len(ctx["base_data"]),
        "raw output size differs from the wav data size",
    )


def scenario_rom_roundtrip(checks, ctx):
    voice_copy = ctx["work"] / "voice-copy"
    shutil.copyfile(ctx["db"], voice_copy)
    code, out = run(ctx["mbrola"], ["-W", voice_copy])
    checks.require(code == 0, "-W ROM dump exited {} ({!r})".format(code, out[:200]))
    rom = Path(str(voice_copy) + ".rom")
    checks.require(rom.is_file(), "ROM image was not created")
    checks.require(
        rom.stat().st_size > voice_copy.stat().st_size,
        "ROM image is smaller than the source database",
    )

    rom_wav = ctx["work"] / "rom-render.wav"
    code, out = run(ctx["mbrola"], ["-w", voice_copy, ctx["pho"], rom_wav])
    checks.require(code == 0, "ROM render exited {} ({!r})".format(code, out[:200]))
    checks.require(
        rom_wav.read_bytes() == (ctx["work"] / "direct.wav").read_bytes(),
        "ROM render differs from the direct render",
    )


def scenario_error_recovery(checks, ctx):
    score = ctx["work"] / "unknown-phoneme.pho"
    score.write_text("Q 100\n_ 100\n", encoding="ascii")

    code, out = run(ctx["mbrola"], [ctx["db"], score, ctx["work"] / "strict.wav"])
    checks.require(code != 0, "unknown phoneme was accepted without -e (exit {})".format(code))
    checks.require("Unknown" in out, "unknown phoneme message missing: {!r}".format(out[:200]))

    lenient = ctx["work"] / "lenient.wav"
    code, out = run(ctx["mbrola"], ["-e", ctx["db"], score, lenient])
    checks.require(code == 0, "-e recovery exited {} ({!r})".format(code, out[:200]))
    _, _, data = read_wav(lenient)
    duration = len(data) / 2.0 / SAMPLE_RATE
    checks.require(0.15 <= duration <= 0.25, "-e output duration {:.3f}s out of range".format(duration))


SCENARIOS = [
    ("fixtures", scenario_fixtures),
    ("cli_contract", scenario_cli_contract),
    ("database_info", scenario_database_info),
    ("real_synthesis", scenario_real_synthesis),
    ("runtime_options", scenario_runtime_options),
    ("output_formats", scenario_output_formats),
    ("rom_roundtrip", scenario_rom_roundtrip),
    ("error_recovery", scenario_error_recovery),
]


def main(argv):
    if len(argv) != 4:
        raise SystemExit("usage: test_mbrola_consumer.py <mbrola> <mbrola-gr2-root> <workdir>")
    mbrola = Path(argv[1])
    gr2_root = Path(argv[2])
    workdir = Path(argv[3])
    work = workdir / "mbrola-consumer"
    work.mkdir(parents=True, exist_ok=True)

    db = gr2_root / GR2_VOICE_REL
    pho = gr2_root / GR2_PHO_REL
    durations = parse_pho(pho)

    ctx = {
        "mbrola": mbrola,
        "db": db,
        "pho": pho,
        "work": work,
        "pho_durations": durations,
        "pho_ms": sum(durations),
    }

    if abs(ctx["pho_ms"] - EXPECTED_PHO_MS) > 1.0:
        raise AssertionError(
            "upstream GR2 score total changed: {} ms".format(ctx["pho_ms"])
        )

    total = 0
    for name, func in SCENARIOS:
        checks = Checks(name)
        func(checks, ctx)
        total += checks.count
        print("  [ok] {:<18} {} assertions".format(name, checks.count))

    print("mbrola consumer validation: {0}/{0} assertions passed".format(total))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
