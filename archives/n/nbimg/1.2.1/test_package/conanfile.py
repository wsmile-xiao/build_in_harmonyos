#!/usr/bin/env python3
"""Conan test_package — nbimg 1.2.1.

Runs a real BMP->NB->BMP round trip against the installed `nbimg` binary:
a synthetic 320x240 24bpp BMP is generated, converted to NB (QVGA,
262144 bytes with HTC signature + padding), converted back to BMP, and the
byte-exact sizes of both outputs are asserted.
"""
import os
import struct
import tempfile

from conan import ConanFile


class NbimgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _make_bmp(path, w, h):
        # 24bpp bottom-up BMP, red pixels (BGR = 00 00 FF)
        pixels = b"\x00\x00\xff" * (w * h)
        file_header = struct.pack("<2sIHHI", b"BM", 54 + len(pixels), 0, 0, 54)
        dib = struct.pack(
            "<IiiHHIIiiII", 40, w, h, 1, 24, 0,
            len(pixels), 2835, 2835, 0, 0,
        )
        with open(path, "wb") as f:
            f.write(file_header + dib + pixels)

    def test(self):
        # R32: only meaningful on Linux/OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            return
        pkg = self.dependencies["nbimg"].package_folder
        exe = os.path.join(pkg, "bin", "nbimg")
        with tempfile.TemporaryDirectory() as tmp:
            bmp = os.path.join(tmp, "test.bmp")
            self._make_bmp(bmp, 320, 240)  # 54 + 320*240*3 = 230454 bytes
            # BMP -> NB (QVGA: 320x240 pixels + 108512 padding + 32-byte HTC
            # signature = 153600 + 108512 + 32 = 262144 bytes)
            self.run(f'"{exe}" -F "{bmp}"', env="conanrun")
            nb = bmp + ".nb"
            assert os.path.getsize(nb) == 262144, f"unexpected NB size: {os.path.getsize(nb)}"
            # NB -> BMP (autodetected QVGA 240x320 -> 54 + 240*320*3 bytes)
            self.run(f'"{exe}" -F "{nb}"', env="conanrun")
            out = nb + ".bmp"
            assert os.path.getsize(out) == 230454, f"unexpected BMP size: {os.path.getsize(out)}"
        self.output.info("nbimg round-trip test passed (BMP->NB->BMP, sizes verified)")