#!/usr/bin/env python3
"""Conan test_package for mp3cat 0.5 — real CLI behavior verification.

Upstream ships no test suite (no tests/, no `make check` target, no test
source files — see MANIFEST.yml for evidence).  This consumer test fills
that gap by exercising mp3cat's core stream-copy / frame-cleaning logic
with minimal, programmatically-constructed MP3 frame fixtures whose SHA256
is verified before use (no opaque binary blobs committed).
"""
import hashlib
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException


class Mp3catTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    # ── Minimal MP3 frame fixture ──────────────────────────────────────
    # Header 0xFF 0xFF 0x28 0x00 = MPEG-1 (version=3), Layer I (layer=3),
    # 64 kbps (bitrate_index=5), 32000 Hz (samplerate_index=2), no padding.
    # frame_length() in frame.c computes: (12 * 64000 / 32000 + 0) * 4 = 96 bytes.
    # mp3cat requires TWO consecutive valid frames (lookahead) before emitting,
    # so N identical frames yield N-1 in the output.
    _FRAME = bytes([0xFF, 0xFF, 0x28, 0x00]) + bytes(92)          # 96-byte frame
    _THREE_FRAMES = _FRAME * 3                                     # 288 bytes
    _DIRTY = b"GARBAGE_NOT_MP3" + _FRAME * 3                       # 303 bytes

    # SHA256 audit checkpoints (verified against a native patched build)
    _THREE_FRAMES_SHA = "d2d66ee01b2a54982741fb494590f564d07ac57c3fbfc2b5bd3c715965c9e500"
    _DIRTY_SHA = "b4959cf3dd5bd0cc69d6ad31a33cb3bff3f33b2b6f6ce909cf553858692641b7"
    # Expected output: 2 frames (192 bytes) — lookahead drops the trailing frame
    _OUTPUT_SHA = "8494b27c66cb1730a83104d6909ee027633ef933c7851d1ccb178d62dd69003d"
    _OUTPUT_LEN = 192

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify fixture integrity before use (requirement: audit fixture SHA)
        three_sha = hashlib.sha256(self._THREE_FRAMES).hexdigest()
        assert three_sha == self._THREE_FRAMES_SHA, \
            f"three_frames fixture SHA mismatch: {three_sha}"
        dirty_sha = hashlib.sha256(self._DIRTY).hexdigest()
        assert dirty_sha == self._DIRTY_SHA, \
            f"dirty fixture SHA mismatch: {dirty_sha}"

        tmp = tempfile.mkdtemp(prefix="mp3cat_test_")
        three_path = os.path.join(tmp, "three.mp3")
        dirty_path = os.path.join(tmp, "dirty.mp3")
        with open(three_path, "wb") as f:
            f.write(self._THREE_FRAMES)
        with open(dirty_path, "wb") as f:
            f.write(self._DIRTY)

        # Discover a shell (not hardcoded — checks PATH, then profile CONFIG_SHELL)
        shell = shutil.which("bash") or os.environ.get("CONFIG_SHELL") or "sh"
        script = os.path.join(self.source_folder, "test.sh")

        # Run the behavior test script (exit-code + output-size checks inside)
        self.run(f'"{shell}" "{script}" "{three_path}" "{dirty_path}" "{tmp}"',
                 env="conanrun")

        # Verify output files (concatenation results + SHA)
        out1 = self._read(os.path.join(tmp, "out_passthrough.mp3"))
        assert len(out1) == self._OUTPUT_LEN, \
            f"passthrough: expected {self._OUTPUT_LEN} bytes, got {len(out1)}"
        assert hashlib.sha256(out1).hexdigest() == self._OUTPUT_SHA, \
            f"passthrough output SHA mismatch"

        out2 = self._read(os.path.join(tmp, "out_clean.mp3"))
        assert len(out2) == self._OUTPUT_LEN, \
            f"cleaning: expected {self._OUTPUT_LEN} bytes, got {len(out2)}"
        assert hashlib.sha256(out2).hexdigest() == self._OUTPUT_SHA, \
            f"cleaning output SHA mismatch"
        # Cleaning must produce identical output to pure passthrough
        assert out1 == out2, "cleaning output differs from passthrough output"

    @staticmethod
    def _read(path):
        with open(path, "rb") as f:
            return f.read()
