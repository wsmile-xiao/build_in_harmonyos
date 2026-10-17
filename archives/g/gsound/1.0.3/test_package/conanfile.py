#!/usr/bin/env python3
"""Conan test_package for gsound 1.0.3 — Conan L1 official test.

Builds test_gsound.c (real GSound API: GSoundContext creation, init, set
attributes, play, cache) with CMake (CMakeDeps + CMakeToolchain) and runs
it. The binary is wrapped with bash because OHOS /system/bin/sh (mksh) cannot
exec ELF binaries directly.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GsoundTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # Explicit generators replace conan's default set; must include
    # VirtualRunEnv/VirtualBuildEnv — without them, test() env="conanrun"
    # misses LD_LIBRARY_PATH (libsoup3 evidence).
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # glib2 must be explicit: gsound public headers include glib/gio/gobject,
        # and CMakeDeps generates empty data for transitive deps (libsoup3
        # evidence). libcanberra is needed at runtime (gsound's NEEDED chain).
        self.requires("glib2/2.88.0")
        self.requires("libcanberra/0.30")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # OHOS musl loader ignores LD_LIBRARY_PATH, so embed RPATH pointing at
        # the (shared) dependency lib dirs in the test binary.
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
        # OHOS loader ignores LD_LIBRARY_PATH and the conan toolchain sets
        # CMAKE_SKIP_RPATH, so CMAKE_BUILD_RPATH has no effect. Embed the rpath
        # directly via linker flags (-Wl,-rpath). musl's dynlink only honors
        # legacy DT_RPATH, not DT_RUNPATH (lld's default), so also pass
        # --disable-new-dtags to force DT_RPATH.
        if rpaths:
            linker_flags = " ".join(
                ["-Wl,--disable-new-dtags"] + ["-Wl,-rpath,%s" % p for p in rpaths]
            )
            configure_vars = {"CMAKE_EXE_LINKER_FLAGS": linker_flags}
        else:
            configure_vars = {}
        cmake.configure(variables=configure_vars)
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        # Collect all dependency libdirs (including transitive glib2/libcanberra
        # and libcanberra's own transitive deps) to build LD_LIBRARY_PATH
        # (cannot rely on conanrun alone — see libsoup3 evidence).
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
        syslib = "/storage/Users/currentUser/usr/local/lib"
        if syslib not in libdirs:
            libdirs.append(syslib)
        ldpath = os.pathsep.join(libdirs)
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_gsound'",
            env="conanrun")
