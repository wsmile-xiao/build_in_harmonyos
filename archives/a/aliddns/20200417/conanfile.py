#!/usr/bin/env python3
"""Conan recipe for aliddns/po2lmo — PO to LMO (Lua Machine Objects) conversion tool.

Source: gghnicole/aliddns (OpenWrt LuCI for AliDDNS). The upstream tarball bundles
an OpenWrt shell-package plus a standalone C tool `po2lmo` under tools/po2lmo/.
Only the C tool is portable; this recipe builds `po2lmo` (a command-line utility)
and installs it to bin/.

Build system: raw Makefile (no ./configure). The Makefile relies on the implicit
`.c.o:` rule, so we pass CC/AR/RANLIB explicitly via Conan conf (R33).

Reference: docs/ADAPTATION_GUIDE.md §4.3 Makefile projects.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AliddnsConan(ConanFile):
    name = "aliddns"
    # Upstream ghnicole/aliddns has no release tag; po2lmo tool is unversioned.
    # Use the latest upstream commit date (2020-04-17) as a legal Conan semver.
    version = "20200417"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: compiler paths come from Conan conf, never from shell env vars.
        # No CMake/Autotools toolchain needed for a raw Makefile; we read conf
        # directly in build() so the values are fresh per Conan step.
        pass

    def _compiler_executables(self):
        # R33: tools.build:compiler_executables is a dict ({"c": ..., "cpp": ...});
        # the per-language keys tools.build:compiler_executables:c do not exist.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c") or "clang"
        ar = executables.get("ar") or "llvm-ar"
        ranlib = executables.get("ranlib") or "llvm-ranlib"
        return cc, ar, ranlib

    def build(self):
        apply_conandata_patches(self)
        # R33: query Conan conf inside build() — instance attrs set in generate()
        # are not reliably persisted across Conan steps.
        cc, ar, ranlib = self._compiler_executables()
        # The upstream Makefile lives in tools/po2lmo and builds src/po2lmo.
        # Conan 2.x basic_layout copies sources to build_folder, but the copy
        # lands at the build folder root (.../b), NOT at self.build_folder which
        # is the build-type subfolder (.../b/build-release). make -C needs the
        # actual dir containing Makefile. source_folder points at the source
        # cache where the Makefile unconditionally exists, and Conan's build()
        # runs make with cwd=build_folder — make -C <abs source dir> works
        # regardless of cwd. Verified: attempt-30451 make ran here and produced
        # tools/po2lmo/src/po2lmo inside source_folder successfully.
        make_dir = os.path.join(self.source_folder, "tools", "po2lmo")
        # R9: -j1 (HMBS injects tools.build:jobs=1 anyway).
        # R33: CC/AR/RANLIB from Conan conf, not shell.
        self.run(
            f"make -C \"{make_dir}\" -j1 CC={cc} AR={ar} RANLIB={ranlib}",
            env="conanbuild",
        )

    def package(self):
        # make ran in source_folder (see build()), so po2lmo dropped there.
        src_dir = os.path.join(self.source_folder, "tools", "po2lmo", "src")
        dst_bin = os.path.join(self.package_folder, "bin")
        # Conan's copy(self, pattern, src, dst) treats `src` as a DIRECTORY and
        # globs `pattern` inside it — passing a file path as src makes copy
        # silently skip (no error, no copy), which then trips a misleading
        # FileNotFoundError at chmod. Pass the src dir + pattern="po2lmo"
        # (same idiom as archives/a/abootimg/0.6 line 93).
        copy(self, "po2lmo", src=src_dir, dst=dst_bin, keep_path=False)
        # Guard: fail loudly if copy() silently skipped, instead of letting
        # chmod raise an opaque FileNotFoundError.
        packaged = os.path.join(dst_bin, "po2lmo")
        if not os.path.isfile(packaged):
            raise AssertionError(
                f"po2lmo not packaged: expected {os.path.join(src_dir, 'po2lmo')} -> {packaged}"
            )
        # Conan's copy() preserves the source file's mode bits, but on OHOS
        # the binary ends up without +x (Error 127 "inaccessible or not found"
        # when test_package tries to exec it). Force 0o755 so the packaged
        # po2lmo is runnable. Same pattern as archives/a/abootimg/0.6 and
        # archives/a/acedb/4.9.62.
        if os.name != "nt":
            os.chmod(packaged, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
