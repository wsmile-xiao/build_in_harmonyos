#!/usr/bin/env python3
"""test_package for libcotp 4.2.1.

Verifies the real public API of libcotp (TOTP/HOTP generation) by compiling,
linking, and executing a test program against the Conan-installed package.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv

required_conan_version = ">=2.0.0"


class LibCotpTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    # ── portable compiler resolution ──────────────────────────────

    def _resolve_portable_compiler(self, configured):
        """Resolve a usable C compiler path portably.

        The CI sandbox may rewrite tools.build:compiler_executables to a path
        that exists in the sandbox but NOT in the current execution env (e.g.
        /data/service/hnp/bin/clang).  When the configured path is missing we
        fall back to a PATH lookup of the compiler's basename, then verify it
        is the correct OHOS aarch64 cross-compiler via -print-target-triple.

        - Never hardcodes a currentUser / SDK-version / absolute host path.
        - Preserves the configured path when it actually exists.
        """
        if configured and os.path.isfile(configured):
            return configured
        # Fallback: lookup the basename (or 'clang') on PATH.
        name = os.path.basename(configured) if configured else "clang"
        resolved = shutil.which(name) or shutil.which("clang")
        if not resolved:
            return configured  # let CMake surface its own error
        # Verify it targets aarch64 (OHOS or generic aarch64), not host.
        try:
            triple = subprocess.run(
                [resolved, "-print-target-triple"],
                capture_output=True, text=True, timeout=15,
            ).stdout.strip()
        except Exception:
            triple = ""
        if "aarch64" in triple:
            return resolved
        return configured

    def _apply_ohos_runtime_fixes(self):
        """OHOS-only: resolve the compiler portably, then (1) prepend the SDK
        LLVM runtime lib dir to LD_LIBRARY_PATH (lld needs libxml2.so.16) and
        (2) export CC/CXX so CMake picks the resolved compiler.  Derived
        dynamically from the resolved compiler path; no hardcoded SDK version
        or currentUser absolute path in the recipe.
        """
        if self.settings.os != "OHOS":
            return
        compilers = self.conf.get(
            "tools.build:compiler_executables", check_type=dict
        ) or {}
        cc = self._resolve_portable_compiler(compilers.get("c"))
        cxx = self._resolve_portable_compiler(compilers.get("cpp"))
        # If the configured path is missing, export CC/CXX to the resolved
        # binary so CMake's native CC/CXX env-var handling picks it up — we do
        # NOT touch tc.variables to avoid clashing with CMakeToolchain's own
        # compiler handling.
        configured_cc = compilers.get("c")
        if cc and (not configured_cc or not os.path.isfile(configured_cc)):
            os.environ["CC"] = cc
        configured_cxx = compilers.get("cpp")
        if cxx and (not configured_cxx or not os.path.isfile(configured_cxx)):
            os.environ["CXX"] = cxx
        # lld/libxml2 runtime: derive lib dir from the resolved compiler.
        if cc:
            bin_dir = os.path.dirname(cc)
            llvm_dir = os.path.dirname(bin_dir)
            lib_dir = os.path.join(llvm_dir, "lib")
            if os.path.isdir(lib_dir):
                existing = os.environ.get("LD_LIBRARY_PATH", "")
                os.environ["LD_LIBRARY_PATH"] = (
                    lib_dir + (os.pathsep + existing if existing else "")
                )
                env = Environment()
                env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                env.vars(self).save_script("ohos_lld_runtime_testpkg")

    def generate(self):
        self._apply_ohos_runtime_fixes()

        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            dep = self.dependencies["libcotp"]
            libdirs = list(dep.cpp_info.libdirs)
            if bool(dep.options.shared) and libdirs:
                tc.variables["LIBCOTP_TEST_RPATH"] = libdirs[0]

        tc.generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    # ── build + test ───────────────────────────────────────────────

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Real execution of the test binary against the Conan-installed
        # libcotp package.  The test program calls the public libcotp API and
        # asserts on the generated TOTP/HOTP output.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_cotp"),
                 env="conanrun")
