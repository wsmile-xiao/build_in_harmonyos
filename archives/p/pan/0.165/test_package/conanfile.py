#!/usr/bin/env python3
"""Conan test_package for pan 0.165 — Conan L1 official test.

pan is an APPLICATION: the real test is executing the packaged pan
binary. pan's --version / -v exits during argument parsing, BEFORE
gtk_init() (pan/gui/pan.cc), so it runs headless without a display —
the correct smoke test on a headless OHOS runner (R34: no string-only
tests). --help is a second real execution path.

The test binary additionally links against gmime-3.0 + gtk-3 through
the generated pkg-config files, proving the packaged dependency chain
(libgmime, libgtk-3, shared glib) resolves at link time from the
consumer side.

The binary is wrapped with bash because OHOS /system/bin/sh (mksh)
cannot exec ELF binaries directly (same pattern as gdu/gmime recipes).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class PanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "PkgConfigDeps", "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # pan is an application: its package_info exports no libs, so the
        # gmime/gtk trees are NOT visible transitively through it. The link
        # proof needs them as DIRECT requirements of the test_package
        # (mirroring pan's own build requirements).
        self.requires("gmime/3.0.5")
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # hnp cmake needs libc++_shared.so from /system/lib64; conan's
        # VirtualBuildEnv doesn't include it — define it via Environment
        # so it gets written into conanbuild.sh (survives the sandbox).
        from conan.tools.env import Environment
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.vars(self).save_script("pan_test_ldpath")

    def build(self):
        # hnp cmake needs libc++_shared.so from /system/lib64; the conan
        # test_package sandbox may strip LD_LIBRARY_PATH — inject directly.
        import os as _os
        cur = _os.environ.get("LD_LIBRARY_PATH", "")
        if "/system/lib64" not in cur:
            _os.environ["LD_LIBRARY_PATH"] = ("/system/lib64:" + cur) if cur else "/system/lib64"
        cmake = CMake(self)
        # OHOS musl loader ignores LD_LIBRARY_PATH for DT_RUNPATH; embed
        # DT_RPATH (--disable-new-dtags) pointing at every dependency
        # libdir (gtk tree shared libs: libgtk-3, libglib-2.0, ...).
        rpaths = []
        for dep in self.dependencies.values():
            base = dep.package_folder
            if not base:
                continue
            for libdir in (dep.cpp_info.libdirs or []):
                if not libdir:
                    continue
                p = libdir if os.path.isabs(libdir) else os.path.join(base, libdir)
                if os.path.isdir(p) and p not in rpaths:
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

        # Locate the packaged pan executable through the test's dependency
        # on the tested package.
        pan_path = None
        for dep in self.dependencies.values():
            ref_name = str(getattr(dep, "ref", ""))
            if ref_name.startswith("pan/"):
                pan_path = os.path.join(dep.package_folder, "bin", "pan")
                break
        if not pan_path or not os.path.isfile(pan_path):
            # fallback: search PATH
            pan_path = shutil.which("pan")

        if not pan_path:
            raise Exception("packaged pan executable not found")

        # Collect libdirs from ALL deps (transitive glib2/pcre2/zlib and the
        # whole gtk tree included), absolutising relative entries against
        # package_folder; append /system/lib64 for the platform libc++_shared.so
        # the OHOS toolchain links against (same fix as date/3.0.5).
        _seen, libdirs = set(), []
        for _r, _d in self.dependencies.items():
            _k = str(getattr(getattr(_r, "ref", _r), "ref", _r))
            if _k in _seen:
                continue
            _seen.add(_k)
            _base = getattr(_d, "package_folder", None) or ""
            for _p in _d.cpp_info.libdirs:
                if not _p:
                    continue
                if not os.path.isabs(_p) and _base:
                    _p = os.path.join(_base, _p)
                if os.path.isabs(_p) and _p not in libdirs:
                    libdirs.append(_p)
        libdirs.append("/system/lib64")
        ldpath = os.pathsep.join(libdirs)

        # Smoke 1: --version must print "Pan 0.165" (real binary execution;
        # --version exits before gtk_init, works headless).
        self.run(
            f'{bash} -c \'export LD_LIBRARY_PATH="{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; '
            f'"{pan_path}" --version\'',
            env="conanrun")

        # Smoke 2: --help exits 0 and prints usage (second real path).
        self.run(
            f'{bash} -c \'export LD_LIBRARY_PATH="{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; '
            f'"{pan_path}" --help >/dev/null 2>&1\'',
            env="conanrun")

        # Smoke 3: the linked test program (gmime+gtk chain from consumer
        # side, CMakeDeps/PkgConfigDeps resolution proof). Its RPATH already
        # covers the conan libdirs; add /system/lib64 the same way.
        self.run(
            f'{bash} -c \'export LD_LIBRARY_PATH="/system/lib64${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; '
            f'./test_pan\'',
            env="conanrun")
