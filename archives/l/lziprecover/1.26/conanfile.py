#!/usr/bin/env python3
"""Conan recipe for lziprecover 1.26 — data recovery tool for .lz files.

lziprecover is a C++ command-line recovery/decompressor (not a library),
from the lzip family by Antonio Diaz Diaz. It uses a custom configure script
(not GNU autoconf), same as lzip.

E095: the configure script does NOT read the $CXX env var; it requires
      CXX=<compiler> as a command-line argument.
R33:  the compiler is obtained from Conan conf (tools.build:compiler_executables),
      never from shell env vars.
OHOS: every link step (lzip helper, lziprecover configure/make, make check)
      runs inside _ohos_lld_env(), which prepends the SDK LLVM host lib dir
      (discovered via `clang++ -print-resource-dir`, verified to contain
      libxml2.so.16) to LD_LIBRARY_PATH so lld can load the matching
      libxml2.so.16 — otherwise lld fails with
      "Error loading shared library libxml2.so.16 ... xmlFreeDoc: symbol not
      found". OHOS-only, dynamic, no hard-coded SDK paths. Same verified
      pattern as test_package/ and libcello/2.1.0.

The official testsuite (make check → testsuite/check.sh) requires the `lzip`
compressor as a helper (LZIP_NAME, defaults to `lzip`). lzip is not published
to the OHOS registry, so to run the full official test suite with zero
external dependencies we build lzip from its own upstream source inside
build() and pass it via LZIP_NAME.
"""
import os
import subprocess
from contextlib import contextmanager

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LziprecoverConan(ConanFile):
    name = "lziprecover"
    version = "1.26"
    description = "Data recovery tool and decompressor for lzip (.lz) compressed files"
    license = "GPL-2.0+"
    homepage = "https://www.nongnu.org/lzip/lziprecover.html"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        # lziprecover source — top-level (strip_root removes lziprecover-1.26/)
        get(self, **self.conan_data["sources"]["lziprecover"], strip_root=True)
        # lzip source — build-time helper for the official testsuite;
        # lzip is not on the OHOS registry, so build it from upstream source.
        get(
            self,
            **self.conan_data["sources"]["lzip"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "lzip-src"),
        )

    # ── Compiler + OHOS linker-runtime helpers ──────────────────────────

    def _get_cxx(self):
        # R33: compiler comes from the Conan conf, never from bare shell
        # variables. The dict form is required for conan 2.29.1.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("cpp") or "clang++"

    @staticmethod
    def _ohos_lld_libdir(cxx):
        """LLVM host lib dir of the active compiler (contains libxml2.so.16).

        The OHOS clang++ driver spawns `lld` for linking, and lld
        dynamically loads libxml2.so.16 from the LLVM distribution's host
        lib dir (the sibling `lib/` of the clang executable). On CI workers
        the ambient LD_LIBRARY_PATH can shadow that dir with an
        incompatible libxml2.so.16, making lld fail:
          Error loading shared library libxml2.so.16
            ... xmlFreeDoc: symbol not found
        We discover that dir dynamically — prefer
        `clang++ -print-resource-dir` -> <prefix>/lib/clang/<ver>, whose
        parent's parent is <prefix>/lib; fall back to the clang sibling
        ../lib. Returns "" unless libxml2.so.16 actually exists there. No
        SDK version or machine-specific path is hard-coded.
        """
        # Path 1: -print-resource-dir -> <prefix>/lib
        try:
            res = subprocess.run(
                [cxx, "-print-resource-dir"],
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.SubprocessError):
            res = None
        if res and res.returncode == 0 and res.stdout.strip():
            hostlib = os.path.dirname(os.path.dirname(res.stdout.strip()))
            if os.path.exists(os.path.join(hostlib, "libxml2.so.16")):
                return hostlib
        # Path 2: <cxx_dir>/../lib
        cxx_dir = os.path.dirname(os.path.realpath(cxx))
        cand = os.path.realpath(os.path.join(cxx_dir, "..", "lib"))
        return cand if os.path.exists(os.path.join(cand, "libxml2.so.16")) else ""

    @contextmanager
    def _ohos_lld_env(self):
        """Prepend the OHOS LLVM host lib dir to LD_LIBRARY_PATH (OHOS only).

        Saves the prior LD_LIBRARY_PATH and restores it on exit, so the
        environment is not mutated for unrelated steps. No-op on non-OHOS.
        """
        if str(self.settings.os) != "OHOS":
            yield
            return
        cxx = self._get_cxx()
        extra = self._ohos_lld_libdir(cxx) if cxx else ""
        saved = os.environ.get("LD_LIBRARY_PATH")
        if extra:
            cur = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = (
                extra + (os.pathsep + cur if cur else "")
            )
            self.output.info(
                f"OHOS lld runtime: LD_LIBRARY_PATH+={extra}"
            )
        try:
            yield
        finally:
            if saved is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = saved

    # ── generate / build / package / package_info ───────────────────────

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E095: custom configure (not autoconf) ignores $CXX; pass CXX= as arg.
        tc.configure_args.append(f"CXX={self._get_cxx()}")
        tc.generate()

    def build(self):
        cxx = self._get_cxx()

        # ── Build lzip helper (testsuite/check.sh needs it via LZIP_NAME) ──
        # Wrapped in _ohos_lld_env(): the final `make` link of the lzip
        # binary invokes lld, which must find the matching libxml2.so.16.
        # This is the exact step that failed in CI #32476.
        lzip_src = os.path.join(self.source_folder, "lzip-src")
        with self._ohos_lld_env():
            self.run(
                f'cd "{lzip_src}" && ./configure CXX="{cxx}" && make -j1',
                env="conanbuild",
            )
        lzip_exe = os.path.join(lzip_src, "lzip")

        # ── Build lziprecover (custom configure, out-of-source via Autotools) ──
        # configure compiles feature probes (-> lld); make links lziprecover
        # (-> lld). Wrap both in the same OHOS linker-runtime env.
        autotools = Autotools(self)
        with self._ohos_lld_env():
            autotools.configure()
            autotools.make(args=["-j1"])

        # ── Run official upstream testsuite (make check, ~864 assertions) ──
        # check.sh runs ~864 assertions across 10 sections; exits non-zero
        # on the first failure. LZIP_NAME points to the lzip we just built.
        # Wrapped: check may relink test helpers via lld. No || true /
        # ignore_errors / skip: a failure must fail conan create.
        with self._ohos_lld_env():
            self.run(
                f'cd "{self.build_folder}" && LZIP_NAME="{lzip_exe}" make check',
                env="conanbuild",
            )

    def package(self):
        # OHOS lacks the `install` coreutil → use Conan copy (zero patch).
        # Makefile install-bin would do: cp ./lziprecover -> $(bindir).
        copy(
            self,
            "lziprecover",
            self.build_folder,
            os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
