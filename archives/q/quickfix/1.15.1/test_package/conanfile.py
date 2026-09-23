#!/usr/bin/env python3
"""test_package for quickfix 1.15.1 — real consumer test.

Compiles a consumer program against the installed quickfix package
(headers + static lib) with the OHOS clang and runs it.  Compiled as C++11:
the quickfix 1.15.1 headers use dynamic exception specifications
(`throw(...)`), removed in C++17, so a consumer cannot compile this package
under the profile default cppstd=17 — the recipe forces `-std=c++0x`
(C++11) for the library itself and the test mirrors that.

The consumer exercises the public FIX API only (message build/serialize/
parse round trip, Dictionary, SessionID).  quickfix 1.15.1 has no version
macro in its public API (upstream configure.ac is itself stale at 1.14.3),
so the assertions are behavioral; the release identity is anchored by the
sha256-pinned v1.15.1 tag archive.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class QuickfixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "build"
        self.folders.generators = "build/conan"

    def _check_package_layout(self):
        pkg = self.dependencies[
            self.tested_reference_str].package_folder
        checks = [
            ("static library", os.path.join(pkg, "lib", "libquickfix.a")),
            ("public header", os.path.join(pkg, "include", "quickfix",
                                           "Message.h")),
            ("FIX 4.4 header dir", os.path.join(pkg, "include", "quickfix",
                                                "fix44", "Message.h")),
            ("pkg-config metadata", os.path.join(pkg, "lib", "pkgconfig",
                                                 "quickfix.pc")),
        ]
        missing = [name for name, path in checks if not os.path.exists(path)]
        if missing:
            raise ConanException(
                "missing quickfix artifacts: " + ", ".join(missing))

    def build(self):
        # clang needs a writable tmpdir (host /tmp is read-only on OHOS).
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        cxx = shutil.which(os.environ.get("CXX", "clang++")) or "clang++"
        pkg = self.dependencies[self.tested_reference_str].package_folder
        src = os.path.join(self.source_folder, "test_consumer.cpp")
        exe = os.path.join(self.build_folder, "test_consumer")
        flags = " ".join([
            "-std=c++11",
            f"-I{pkg}/include/quickfix",
            f"-L{pkg}/lib",
            "-Wl,-rpath,'$ORIGIN'",
            "-lquickfix",
        ])
        self.run(f"{cxx} -o {exe} {src} {flags}")

    def test(self):
        self._check_package_layout()
        if cross_building(self):
            self.output.info("cross-building: link-only verification")
            return
        bash = (os.environ.get("CONFIG_SHELL")
                or shutil.which("bash") or "bash")
        exe = os.path.join(self.build_folder, "test_consumer")
        self.output.info("run quickfix consumer program (public FIX API)")
        self.run(f"{bash} -c '{exe}'", env="conanrun")
