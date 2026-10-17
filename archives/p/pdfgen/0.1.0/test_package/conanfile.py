#!/usr/bin/env python3
"""Conan consumer test for pdfgen 0.1.0 — drives the packaged static
library the way a downstream project does:
1. compile the consumer test program with the packaged libpdfgen.a +
   pdfgen.h via CMake (pdfgen::pdfgen target);
2. execute the signed binary (E077) — it generates output.pdf through the
   full public API (pages/text/shapes/barcodes/bookmarks/rgb24) and
   asserts zero API failures;
3. run_check.sh then verifies the generated PDF itself: header magic,
   page count, metadata, bookmark tree, embedded text (utf8 + control
   characters) — the pypdf equivalent of the upstream tests.sh asserts
   (pdftotext/pdftk are not provisioned on the device)."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PdfGenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binp = os.path.join(self.cpp.build.bindirs[0], "test_pdfgen")
        # E077: OHOS only executes ELF files carrying a valid .codesign
        # section; remove the placeholder and self-sign before running.
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if os.path.isfile(signer) and os.path.isfile(objcopy):
            signer_env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", binp],
                capture_output=True, timeout=60, env=signer_env,
            )
            signed = binp + ".signed"
            subprocess.run(
                [signer, "sign", "-inFile", binp, "-outFile", signed, "-selfSign", "1"],
                check=True, timeout=60, env=signer_env,
            )
            os.replace(signed, binp)
        os.chmod(binp, 0o755)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_check.sh")
        self.run(f'{bash} "{script}" "{binp}"', env="conanrun")
