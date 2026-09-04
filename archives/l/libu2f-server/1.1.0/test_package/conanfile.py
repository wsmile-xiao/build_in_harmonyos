#!/usr/bin/env python3
"""test_package for libu2f-server 1.1.0 — consumer test.

Compiles and links a consumer program against libu2f-server,
linking also json-c and openssl (transitive dependencies).
Calls u2fs_init/u2fs_done (read-only, no hardware required).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class Libu2fServerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "PkgConfigDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("json-c/0.17")
        self.requires("openssl/1.1.1w")

    def layout(self):
        self.folders.build = "build"
        self.folders.generators = "build/conan"

    def _check_package_layout(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        checks = [
            ("library", os.path.join(pkg, "lib", "libu2f-server.a")),
            ("header", os.path.join(pkg, "include", "u2f-server", "u2f-server.h")),
        ]
        missing = [name for name, path in checks if not os.path.exists(path)]
        if missing:
            raise ConanException(
                "missing libu2f-server artifacts: " + ", ".join(missing))

    def build(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        cc = shutil.which(os.environ.get("CC", "clang")) or "clang"
        pkg = self.dependencies[self.tested_reference_str].package_folder
        jsonc_pkg = self.dependencies["json-c"].package_folder
        openssl_pkg = self.dependencies["openssl"].package_folder
        src = os.path.join(self.source_folder, "test_consumer.c")
        exe = os.path.join(self.build_folder, "test_consumer")
        flags = " ".join([
            f"-I{pkg}/include",
            f"-I{jsonc_pkg}/include",
            f"-I{jsonc_pkg}/include/json-c",
            f"-I{openssl_pkg}/include",
            f"-L{pkg}/lib",
            f"-L{jsonc_pkg}/lib",
            f"-L{openssl_pkg}/lib",
            "-Wl,--allow-shlib-undefined",
            "-lu2f-server -ljson-c -lssl -lcrypto",
        ])
        self.run(f"{cc} -o {exe} {src} {flags}")

    def test(self):
        self._check_package_layout()
        if cross_building(self):
            self.output.info("cross-building: link-only verification")
            return
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        exe = os.path.join(self.build_folder, "test_consumer")
        self.output.info("run consumer program (read-only API)")
        self.run(f"{bash} -c '{exe}'", env="conanrun")
