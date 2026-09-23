#!/usr/bin/env python3
"""Conan test_package for gmime 3.2.15 — Conan L1 official test.

Builds test.c (real gmime API: GMimeParser message parsing, RFC2047 subject
decode, InternetAddressList handling, message construction + subject
round-trip, stream-filter pipeline, base64 decode) and runs it on the OHOS
aarch64 target. The binary is wrapped with bash because OHOS /system/bin/sh
(mksh) cannot exec ELF binaries directly.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GmimeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv/VirtualBuildEnv must be listed explicitly (declaring
    # generators replaces the default set); without them test() cannot
    # resolve LD_LIBRARY_PATH for the static dependency stack.
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # glib2 must be a direct requirement of the test_package: gmime's
        # public headers include glib.h, and CMakeDeps generates empty data
        # for transitive deps (conan 2.29 behaviour, libsoup3 recipe note).
        self.requires("glib2/2.88.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # OHOS musl loader ignores LD_LIBRARY_PATH; embed RPATH pointing at
        # the dependency lib dirs in the test binary, forcing DT_RPATH
        # (--disable-new-dtags) because musl ignores DT_RUNPATH.
        rpaths = []
        for dep in self.dependencies.values():
            base = dep.package_folder
            if not base:
                continue
            for libdir in (dep.cpp_info.libdirs or []):
                if not libdir:
                    continue
                p = libdir if os.path.isabs(libdir) else os.path.join(base, libdir)
                if os.path.isdir(p):
                    rpaths.append(p)
        if rpaths:
            linker_flags = " ".join(
                ["-Wl,--disable-new-dtags"] + ["-Wl,-rpath,%s" % p for p in rpaths])
            cmake.configure(variables={"CMAKE_EXE_LINKER_FLAGS": linker_flags})
        else:
            cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        # Collect libdirs from ALL deps (transitive glib2/pcre2/zlib included),
        # absolutising relative entries against package_folder.
        _seen, libdirs = set(), []
        for _r, _d in self.dependencies.items():
            _k = str(getattr(getattr(_r, "ref", _r), "ref", _r))
            if _k in _seen:
                continue
            _seen.add(_k)
            _base = getattr(_d, "package_folder", None) or ""
            for _p in _d.cpp_info.libdirs:
                if not os.path.isabs(_p) and _base:
                    _p = os.path.join(_base, _p)
                if _p not in libdirs:
                    libdirs.append(_p)
        ldpath = os.pathsep.join(libdirs)
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_gmime'",
            env="conanrun")
