#!/usr/bin/env python3
"""Conan test_package for libshumate 1.7.0 — Conan L1 official test.

Builds test.c (real libshumate API: map source registry + OSM source zoom/
latitude + ShumateCoordinate + ShumateViewport, no display needed) with CMake
(CMakeDeps + CMakeToolchain) and runs it wrapped in bash (OHOS mksh cannot
exec ELF binaries directly).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibshumateTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # ⚠️ 显式 generators 必须含 VirtualRunEnv/VirtualBuildEnv（libsoup3 教训）
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ⚠️ glib/gtk4 显式直接依赖：CMakeDeps 对传递依赖生成空数据（conan 2.29）
        self.requires("gtk4/4.22.4")
        self.requires("glib/2.84.0.1.1")
        # ⚠️ cairo-gobject 显式直接依赖（CI 红 #12833 根因）：shumate-point.h
        # 直接 #include <cairo-gobject.h>；cairo-gobject 只作为 gtk4 的传递
        # 依赖时 CMakeDeps 生成空数据，编译器按 include 目录序解析到
        # cairo/1.18.4（glib=disabled）的 stub 头 →
        # "cairo-gobject.h:197: error Cairo was not compiled with support
        # for GObject"。显式 requires 后真包（glib=enabled，真头文件）的
        # include 目录进入编译命令且排在传递 cairo 之前。
        self.requires("cairo-gobject/1.18.4")

    def layout(self):
        cmake_layout(self)

    def build(self):
        # OHOS: conan's VirtualBuildEnv rewrites LD_LIBRARY_PATH; the host
        # cmake (/data/service/hnp/bin) needs libc++_shared.so from the SDK
        # lib dir and /system/lib64 — re-inject both (gtksourceview5 lesson).
        for _p in ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
                   "/system/lib64"):
            if os.path.isdir(_p):
                os.environ["LD_LIBRARY_PATH"] = (
                    _p + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
                )
        cmake = CMake(self)
        # Embed RPATH for the shared dependency lib dirs (musl honors legacy
        # DT_RPATH only; force with --disable-new-dtags).
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
                ["-Wl,--disable-new-dtags"] + ["-Wl,-rpath,%s" % p for p in rpaths]
            )
            configure_vars = {"CMAKE_EXE_LINKER_FLAGS": linker_flags}
        else:
            configure_vars = {}
        # CI 红 #12833 双保险：cairo-gobject.h 的
        # `#if CAIRO_HAS_GOBJECT_FUNCTIONS` 在 include 目录序不利时落到
        # stub 的 #error 分支（主配方 _fix_cairo_gobject_pc 同款 R15 修法，
        # 但那是 pkg-config 路径；CMakeDeps 路径用编译定义兜底）。
        configure_vars["CMAKE_C_FLAGS"] = "-DCAIRO_HAS_GOBJECT_FUNCTIONS=1"
        cmake.configure(variables=configure_vars)
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
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
            f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_libshumate'",
            env="conanrun")
