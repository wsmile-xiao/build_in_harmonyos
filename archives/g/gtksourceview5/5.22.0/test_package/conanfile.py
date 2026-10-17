#!/usr/bin/env python3
"""Conan test_package for gtksourceview5 5.22.0 — Conan L1 official test.

Builds test.c (real GtkSourceView 5 API: version functions + language
manager + style scheme manager + buffer creation, no display needed) with
CMake (CMakeDeps + CMakeToolchain) and runs it. The binary is wrapped with
bash because OHOS /system/bin/sh (mksh) cannot exec ELF binaries directly.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Gtksourceview5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # ⚠️ 显式列出 generators 会替换 conan 默认集，必须带上 VirtualRunEnv /
    # VirtualBuildEnv：漏了它们 test() 里 env="conanrun" 拿不到 conanrun
    # 环境的 LD_LIBRARY_PATH（libsoup3 同款教训）。
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ⚠️ glib/gtk4 必须显式声明为 test_package 的直接依赖：
        # gtksourceview5 的公共头 include gtk/glib/gio/gobject，而 CMakeDeps
        # 对「传递依赖」生成空数据（conan 2.29 行为）；显式 requires 后
        # CMakeDeps 生成完整 target，test 编译链接才拿得到头文件与库。
        self.requires("gtk4/4.22.4")
        self.requires("glib/2.84.0.1.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        # OHOS: cmake itself (/data/service/hnp/bin/cmake) is an OHOS ELF
        # that needs libc++_shared.so — when conan rewrites the environment
        # for the build (profile buildenv / VirtualBuildEnv), the inherited
        # LD_LIBRARY_PATH may be reduced to the SDK lib dir only and cmake
        # dies with "Error relocating cmake: _ZdlPv: symbol not found"
        # (exit 127). Prepend BOTH the SDK lib dir and /system/lib64 before
        # invoking cmake (kconfig 6.26.0 precedent).
        for _p in ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
                   "/system/lib64"):
            if os.path.isdir(_p):
                os.environ["LD_LIBRARY_PATH"] = (
                    _p + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
                )
        cmake = CMake(self)
        # OHOS musl loader ignores LD_LIBRARY_PATH for RPATH-less binaries,
        # so embed RPATH pointing at the (shared) dependency lib dirs.
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
        # musl's dynlink only honors legacy DT_RPATH, not DT_RUNPATH (lld's
        # default), so also pass --disable-new-dtags to force DT_RPATH.
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
        # 显式拼 LD_LIBRARY_PATH：遍历全部依赖（含传递 glib/gtk4/pcre2/
        # libxml2/fribidi）收集 libdirs，相对路径用 package_folder 补全。
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
        # XDG_DATA_DIRS: language specs are installed into the package's
        # share/gtksourceview-5 dir; the manager falls back to compile-time
        # paths otherwise (fine, but explicit is better on OHOS).
        pkg = self.dependencies.get(self.tested_reference_str) if hasattr(self, "dependencies") else None
        datadirs = []
        if pkg and getattr(pkg, "package_folder", None):
            datadirs.append(os.path.join(pkg.package_folder, "share"))
        xdg = os.pathsep.join(datadirs) if datadirs else ""
        cmd = f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_gtksourceview5'"
        if xdg:
            cmd = f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; export XDG_DATA_DIRS=\"{xdg}:${{XDG_DATA_DIRS:+$XDG_DATA_DIRS}}\"; ./test_gtksourceview5'"
        self.run(cmd, env="conanrun")
