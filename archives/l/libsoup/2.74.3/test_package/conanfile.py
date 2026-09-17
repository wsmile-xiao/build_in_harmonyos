#!/usr/bin/env python3
"""Conan test_package for libsoup 2.74.3 — Conan L1 official test.

Builds test.c (real libsoup2 API: SoupURI + SoupSession + SoupMessage) with
CMake (CMakeDeps + CMakeToolchain) and runs it. The binary is wrapped with
bash because OHOS /system/bin/sh (mksh) cannot exec ELF binaries directly.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibsoupTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # glib2 must be explicit: libsoup's public headers include
        # glib/gio/gobject, and CMakeDeps generates empty data for
        # transitive deps (conan 2.29 behavior).
        self.requires("glib2/2.88.0")

    def generate(self):
        # cmake 是 HNP 工具链二进制，依赖 libc++_shared.so；conan 构建环境
        # 把 LD_LIBRARY_PATH 覆盖为依赖包 lib 目录，导致 cmake 加载到
        # /data/storage/el1/bundle/libs/arm64 等不兼容 libc++（符号缺失
        # _ZdlPv/_Znwm 等 → Error relocating）。将 /system/lib64（含可用
        # libc++_shared.so）prepend 回构建环境（与 xmlbird libintl 同类修复）。
        self.buildenv_info.prepend_path("LD_LIBRARY_PATH", "/system/lib64")

    def layout(self):
        cmake_layout(self)

    def build(self):
        # cmake 是 HNP 工具链二进制，依赖 libc++_shared.so；conan 构建环境
        # 把 LD_LIBRARY_PATH 覆盖为依赖包 lib 目录，导致 cmake 加载到
        # /data/storage/el1/bundle/libs/arm64 等不兼容 libc++（符号缺失
        # _ZdlPv/_Znwm 等 → Error relocating）。将 /system/lib64（含可用
        # libc++_shared.so）直接 prepend 到进程环境，保证 cmake 子进程
        # 加载到正确 libc++。注意：generate() 的 buildenv_info 在此场景
        # 未被 CMake.configure 的 env 聚合完整，故此处 os.environ 直接
        # 修改为防御性必需（与主配方 generate() 处理 lld 的方式一致）。
        os.environ["LD_LIBRARY_PATH"] = (
            "/system/lib64" + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        )
        cmake = CMake(self)
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
            f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_libsoup'",
            env="conanrun")
