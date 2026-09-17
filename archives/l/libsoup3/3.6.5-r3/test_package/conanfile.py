#!/usr/bin/env python3
"""Conan test_package for libsoup3 3.6.5-r3 — Conan L1 official test.

Builds test.c (real libsoup3 API: SoupURI + SoupSession) with CMake
(CMakeDeps + CMakeToolchain) and runs it. The binary is wrapped with bash
because OHOS /system/bin/sh (mksh) cannot exec ELF binaries directly.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libsoup3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # ⚠️ 显式列出 generators 会**替换** conan 默认集，必须带上 VirtualRunEnv /
    # VirtualBuildEnv：漏了它们 test() 里 env="conanrun" 就拿不到 conanrun
    # 环境的 LD_LIBRARY_PATH，表现为编译链接全过、一跑就报
    # `Error loading shared library libsoup-3.0.so.0`（libpsl 同款实撞）。
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ⚠️ glib 必须显式声明为 test_package 的直接依赖：libsoup3 的公共头文件
        # include glib/gio/gobject，而 CMakeDeps 对「传递依赖」glib 生成空数据
        # （conan 2.29 行为，libsoup3 package_info() 注释同款记录）。显式
        # requires 后 CMakeDeps 生成完整 glib target，test 编译链接才拿得到
        # 头文件与库。版本必须与 libsoup3 链一致：共享 glib/2.84.0.1.1。
        self.requires("glib/2.84.0.1.1", options={"shared": True})

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
                # libdir may be an absolute path (when a recipe appends a
                # dependency's libdir to its own cpp_info.libdirs); join only
                # relative entries, keep absolute ones as-is.
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
        # Fall back through CONFIG_SHELL -> PATH lookup -> known hnp path, so an
        # empty CONFIG_SHELL (some CI unset via "") still resolves a shell.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        # 显式拼 LD_LIBRARY_PATH，不能只依赖 conanrun 环境：VirtualRunEnv 生成
        # 的 conanrunenv 里 libdirs 可能是空的（本仓已记录：shared=False 发布的
        # 包 conan 视为静态、不写 libdirs，但包里确实装了 .so；libpsl 实撞），
        # 症状是编译链接全过、一跑就 `Error loading shared library libsoup-3.0.so.0`。
        # 遍历**全部**依赖（含传递的 glib/libpsl/libnghttp2/sqlite3）收集
        # libdirs，并**把相对路径用 package_folder 补成绝对路径**（否则会出现
        # LD_LIBRARY_PATH 里裸 `lib:` 的无效项，loader 直接找不到库——libpsl
        # 的 build() 注释实撞记录）。r3 起全部依赖均为 conan 共享包（glib/
        # libpsl/libnghttp2/sqlite3），无需再拼接执行端系统库目录。
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
            f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_libsoup3'",
            env="conanrun")
