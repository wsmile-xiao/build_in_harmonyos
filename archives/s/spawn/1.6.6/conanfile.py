#!/usr/bin/env python3
"""Conan recipe for the spawn 1.6.6 package.

The package intentionally uses the competition package name ``spawn`` while
building the upstream project ``spawn-fcgi 1.6.6``.  spawn-fcgi has no
upstream automated test suite; the consumer test_package performs the real
CLI, socket, and FastCGI protocol checks.
"""
import json
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


UPSTREAM_RESULT = {
    "status": "no_tests",
    "framework": "meson",
    "command": "meson test",
    "discovered": 0,
    "executed": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "reason": (
        "spawn-fcgi 1.6.6 has no upstream automated tests. Its top-level "
        "meson.build defines the executable and install_man only, with no "
        "test() call, tests/ subdirectory, check target, or test program."
    ),
}


class SpawnConan(ConanFile):
    name = "spawn"
    version = "1.6.6"
    description = "Simple program to spawn FastCGI processes (upstream spawn-fcgi)"
    license = "BSD-3-Clause"
    homepage = "https://www.lighttpd.net/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = MesonToolchain(self)
        toolchain.generate()

        # Meson's native file can lack a concrete archiver on OHOS.  Derive it
        # from the configured compiler path instead of relying on PATH.
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        with open(native_file, "r", encoding="utf-8") as handle:
            content = handle.read()

        if "ar =" not in content and "ar=" not in content:
            cc_path = None
            for raw_line in content.splitlines():
                line = raw_line.strip()
                if line.startswith("c =") or line.startswith("c="):
                    cc_path = line.split("=", 1)[1].strip().strip("'\"")
                    break
            ar_path = (
                os.path.join(os.path.dirname(cc_path), "llvm-ar")
                if cc_path
                else os.environ.get("AR", "llvm-ar")
            )
            updated = content.replace(
                "[binaries]\nc =", "[binaries]\nar = '%s'\nc =" % ar_path, 1
            )
            if updated == content:
                raise RuntimeError("failed to inject ar into Meson native file")
            with open(native_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(updated)

    def build(self):
        apply_conandata_patches(self)

        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            UPSTREAM_RESULT, ensure_ascii=False
        )
        self.output.info(marker)
        self.output.info(
            "UPSTREAM_TEST_RESULT total=0 failures=0 errors=0 skipped=0"
        )

        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
