#!/usr/bin/env python3
"""Conan test_package for librevisa 0.0.20130812.

Builds test_visa.c (real VISA API: viOpenDefaultRM / viParseRsrc /
viGetAttribute / viClose, 5 deterministic checks, no hardware needed) with
CMake and runs it. Emits the HMBS_TEST_PACKAGE_RESULT marker with real
counts (discovered=5).

NOTE: viStatusDesc must NOT be used here: it is declared in visa.h but
has no implementation in the 0.0.20130812 snapshot (no viStatusDesc.cpp),
so any call fails the static link with "undefined symbol: viStatusDesc".
The C++ static archive is linked through the C++ linker (LINKER_LANGUAGE
CXX in CMakeLists.txt); a C-only project would miss __cxa_*/new/delete/
libc++ symbols.

Consumer-side compiler fallback (zydis precedent): the profile pins
CMAKE_C/CXX_COMPILER to /data/service/hnp/bin/clang which is absent on
some runners, so resolve existence-first (pinned path, sibling toolchain
dir, then PATH) and pin the working compilers via CMake cache variables,
repair the generated toolchain file, and export CC/CXX -- but only when
the pinned path is actually missing (healthy machines: zero change).
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


def _resolve_shell():
    """First existing shell for running the test binary.

    /system/bin/sh (mksh) cannot execute ELF directly, so the test is
    wrapped with a POSIX shell. Profiles pin CONFIG_SHELL to
    /data/service/hnp/bin/bash, which is absent on some runners
    (Error 127); probe existence first, then PATH, instead of trusting
    the pinned absolute path.
    """
    for cand in (
        os.environ.get("CONFIG_SHELL"),
        os.environ.get("SHELL"),
        "/bin/sh",
        "/system/bin/sh",
        "/data/service/hnp/bin/bash",
    ):
        if cand and os.path.isfile(cand):
            return cand
    for name in ("bash", "sh"):
        found = shutil.which(name)
        if found:
            return found
    return "/bin/sh"


def _resolve_compiler(configured, names):
    """Existence-first compiler resolution.

    Pinned path when it exists; otherwise the sibling toolchain dir of
    the pinned path, then ~/usr/local/bin, then PATH. Returns the
    configured value (or names[0]) when nothing is found so the error
    stays explicit.
    """
    if configured and os.path.isfile(configured):
        return configured
    pinned_dir = os.path.dirname(configured) if configured else ""
    if pinned_dir and os.path.isdir(pinned_dir):
        for name in names:
            cand = os.path.join(pinned_dir, name)
            if os.path.isfile(cand):
                return cand
    home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
    if os.path.isdir(home_bin):
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.isfile(cand):
                return cand
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return configured or names[0]


class LibrevisaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default=None)
        except Exception:
            compilers = None
        if not isinstance(compilers, dict):
            compilers = {}
        c = _resolve_compiler(compilers.get("c"), ("clang", "cc", "gcc"))
        cxx = _resolve_compiler(
            compilers.get("cpp"), ("clang++", "c++", "g++"))
        if c:
            tc.cache_variables["CMAKE_C_COMPILER"] = c
        if cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx
        self.output.info("HMBS diag test compilers c=%s cxx=%s" % (c, cxx))
        tc.generate()
        CMakeDeps(self).generate()
        self._fix_generated_toolchain_compiler(compilers, c, cxx)

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        # The cache_variables pin alone may not override the stale profile
        # compiler baked into conan_toolchain.cmake, so replace the
        # confirmed-missing path in the generated file and export CC/CXX --
        # only when the configured path is missing and the resolved one
        # exists (healthy machines: no change at all).
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        if (c_old and c and c_old != c
                and not os.path.isfile(c_old) and os.path.isfile(c)):
            pairs.append((c_old, c))
        if (cxx_old and cxx and cxx_old != cxx
                and not os.path.isfile(cxx_old) and os.path.isfile(cxx)):
            pairs.append((cxx_old, cxx))
        if not pairs:
            return
        try:
            gf = getattr(self, "generators_folder", None)
            path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8",
                          errors="replace") as f:
                    text = f.read()
                orig = text
                for old_p, new_p in pairs:
                    text = text.replace(old_p, new_p)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.output.info(
                        "HMBS diag test fixed toolchain %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag test toolchain fix failed: %s" % e)
        try:
            comp_env = Environment()
            if (c_old, c) in pairs:
                comp_env.define("CC", c)
            if (cxx_old, cxx) in pairs:
                comp_env.define("CXX", cxx)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as e:
            self.output.warning("HMBS diag test compiler env failed: %s" % e)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 5 explicit checks in test_visa.c (see source for the list).
        command = "./test_visa"
        result = {
            "executed": True,
            "passed": False,
            "command": command,
            "discovered": 5,
            "passedCount": 0,
        }
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly,
        # so wrap execution with a probed shell (zlib/libuio precedent).
        bash = _resolve_shell()
        try:
            self.run(f'{bash} -c "./test_visa"', env="conanrun")
        except Exception:
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
            )
            raise
        result["passed"] = True
        result["passedCount"] = 5
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
