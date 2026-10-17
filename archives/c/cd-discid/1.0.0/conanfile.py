#!/usr/bin/env python3
"""Conan recipe for cd-discid 1.0.0 — CDDB discid lookup utility (raw Makefile).

Build system: plain Makefile (no configure script, no autotools).
  - targets: all / clean / install / tarball  (NO upstream `check` target)
The build compiles a single C file (cd-discid.c) with only libc + ioctl.

OHOS lld/libxml2.so.16 host-runtime guard (E120/E321):
  The OHOS clang driver spawns `lld` for linking, and lld's RUNPATH
  ($ORIGIN/../lib) points into the SDK llvm/lib. On CI workers the ambient
  LD_LIBRARY_PATH can shadow that dir with an incompatible libxml2.so.16,
  making lld fail with "Error loading shared library libxml2.so.16 ...
  symbol not found" and clang with "unable to execute command".
  We probe the SDK lld (flavor-aware) and prepend the SDK llvm/lib to
  LD_LIBRARY_PATH ONLY while build()/package() invoke the compiler, never
  while test_package runs the produced ELF (E321 forbid_2).
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class CddiscidConan(ConanFile):
    name = "cd-discid"
    version = "1.0.0"
    description = "CDDB discid lookup utility — reads disc TOC from a CD-ROM and prints the CDDB disc id"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/taem/cd-discid"
    url = "https://github.com/taem/cd-discid"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # R33: compiler from Conan conf, NEVER bare ${CC} shell var.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c", "clang") if compilers else "clang"

    def _sdk_llvm_libdir(self):
        """Locate the active OHOS SDK llvm/lib containing libxml2.so.16.

        Derives candidate dirs from the Conan-configured compiler executable
        and `clang -print-resource-dir`, mirroring abseil PR #5118 (wxjshr).
        Returns "" on non-OHOS or when libxml2.so.16 is absent.
        """
        if str(self.settings.os) != "OHOS":
            return ""

        cc = self._get_cc()
        cc_real = os.path.realpath(cc)
        candidates = []

        # Primary: clang -print-resource-dir → <llvm>/lib/clang/<ver> → <llvm>/lib
        try:
            resource_dir = subprocess.check_output(
                [cc, "-print-resource-dir"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
        except (OSError, subprocess.CalledProcessError):
            pass

        # Fallback: <clang>/../../lib relative to the compiler binary
        candidates.append(
            os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        )

        for candidate in dict.fromkeys(candidates):
            libdir = os.path.join(candidate, "lib")
            if os.path.isfile(os.path.join(libdir, "libxml2.so.16")):
                return libdir
            if os.path.isdir(libdir) and os.path.isfile(
                os.path.join(candidate, "libxml2.so.16")
            ):
                return candidate
        return ""

    def _usable_sdk_llvm_libdir(self):
        """Probe the SDK lld (flavor-aware) and return its llvm/lib on success.

        Raises ConanException if the linker cannot start or fails its
        GNU-flavor probe — fail fast instead of silently producing nothing.
        """
        if str(self.settings.os) != "OHOS":
            return ""

        cached = getattr(self, "_checked_sdk_llvm_libdir", None)
        if cached is not None:
            return cached

        sdk_llvm_lib = self._sdk_llvm_libdir()
        if not sdk_llvm_lib:
            # No SDK libxml2 found; assume the ambient environment is healthy
            # (this matches the non-OHOS path and avoids false failures on
            # workers where lld resolves libxml2 via system paths).
            self._checked_sdk_llvm_libdir = ""
            return ""

        lld = os.path.join(os.path.dirname(sdk_llvm_lib), "bin", "lld")
        probe_env = os.environ.copy()
        old_ld_path = probe_env.get("LD_LIBRARY_PATH", "")
        probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (sdk_llvm_lib, old_ld_path) if part
        )
        try:
            probe = subprocess.run(
                [lld, "-flavor", "gnu", "--version"],
                env=probe_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanException(
                f"Cannot execute the active OHOS SDK linker {lld}: {error}"
            ) from error
        if probe is None or probe.returncode != 0:
            raise ConanException(
                f"The active OHOS SDK linker failed its GNU-flavor probe: {lld}; "
                f"stderr={probe.stderr.strip() if probe else 'n/a'!r}"
            )

        self._checked_sdk_llvm_libdir = sdk_llvm_lib
        return sdk_llvm_lib

    def _build_environment(self):
        """Environment that prepends the SDK llvm/lib to LD_LIBRARY_PATH.

        Applied ONLY around build()/package() compiler invocations, never
        around test_package ELF execution (E321 forbid_2).
        """
        environment = Environment()
        sdk_llvm_lib = self._usable_sdk_llvm_libdir()
        if sdk_llvm_lib:
            # CI shells may prepend ~/usr/local/lib, which can shadow the
            # SDK's ABI-matched libxml2.so.16 and prevent lld from starting.
            self.output.info(
                f"Prepending OHOS SDK linker runtime path: {sdk_llvm_lib}"
            )
            environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return environment

    def build(self):
        apply_conandata_patches(self)

        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("cd-discid requires a POSIX host (Linux or OHOS)")

        cc = self._get_cc()

        # R9: always -j1. Raw Makefile project — run make where the Makefile is.
        # The Makefile defines only `all`/`clean`/`install`/`tarball` targets;
        # there is NO upstream `make check` target (verified from the Makefile).
        # _build_environment() prepends the SDK llvm/lib so lld can find
        # libxml2.so.16 on CI workers with a shadowing ambient LD_LIBRARY_PATH.
        with self._build_environment().vars(self).apply():
            self.run("make -j1 CC={} LDFLAGS=".format(cc), cwd=self.source_folder)

    def package(self):
        # Upstream `make install` needs `/usr/bin/install` (absent on OHOS) and
        # uses `-o 0` (root chown) — copy outputs directly into the package.
        copy(self, "cd-discid", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "cd-discid.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # Command-line tool: no libraries, only bindir.
        self.cpp_info.bindirs = ["bin"]
