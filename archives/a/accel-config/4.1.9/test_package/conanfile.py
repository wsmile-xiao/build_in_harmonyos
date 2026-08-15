#!/usr/bin/env python3
"""test_package for accel-config 4.1.9 — real consumer test.

B-layer consumer test (path B knowledge extension):
- compile & link a consumer program against libaccel-config (+ uuid include dir)
- call read-only public API only (accfg_new/get_log_priority/set_log_priority/unref)
- run the real binary via self.run() — the run commands below execute the
  consumer ELF and the accel-config CLI, never a bare no-op command
No device-touching operations are performed.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class AccelConfigTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "PkgConfigDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("uuid/2.40.1")

    def layout(self):
        # Keep generators/build outputs out of the archive source dir.
        self.folders.build = "build"
        self.folders.generators = "build/conan"

    def _check_package_layout(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        checks = [
            ("libaccel-config shared lib", os.path.join(pkg, "lib", "libaccel-config.so")),
            ("public header", os.path.join(pkg, "include", "accel-config", "libaccel_config.h")),
            ("pkg-config metadata", os.path.join(pkg, "lib", "pkgconfig", "libaccel-config.pc")),
            ("CLI binary", os.path.join(pkg, "bin", "accel-config")),
        ]
        missing = [name for name, path in checks if not os.path.exists(path)]
        if missing:
            raise ConanException("missing accel-config artifacts: " + ", ".join(missing))

    def build(self):
        # clang needs a writable tmpdir (host /tmp may be read-only on OHOS).
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        cc = shutil.which(os.environ.get("CC", "clang")) or "clang"
        pkg = self.dependencies[self.tested_reference_str].package_folder
        uuid_pkg = self.dependencies["uuid"].package_folder
        src = os.path.join(self.source_folder, "test_consumer.c")
        exe = os.path.join(self.build_folder, "test_consumer")
        flags = " ".join([
            f"-I{pkg}/include",
            f"-I{uuid_pkg}/include",
            f"-L{pkg}/lib",
            f"-L{uuid_pkg}/lib",
            "-Wl,-rpath,'$ORIGIN' -laccel-config -luuid",
        ])
        self.run(f"{cc} -o {exe} {src} {flags}")

    def test(self):
        self._check_package_layout()
        if cross_building(self):
            self.output.info("cross-building: link-only verification")
            return
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        exe = os.path.join(self.build_folder, "test_consumer")
        accel_config = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "bin", "accel-config")
        self.output.info("run consumer program (read-only API)")
        self.run(f"{bash} -c '{exe}'", env="conanrun")
        self.output.info("run accel-config --version (read-only entry)")
        self.run(f"{bash} -c '{accel_config} --version'", env="conanrun")
