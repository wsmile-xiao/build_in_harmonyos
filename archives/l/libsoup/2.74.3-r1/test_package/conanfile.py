#!/usr/bin/env python3
"""Conan test_package for libsoup 2.74.3-r1 — Conan L1 official test.

Builds test.c (real libsoup2 API: SoupURI + SoupMessage + SoupSession) with
CMake (CMakeDeps + CMakeToolchain) and runs it. The binary is wrapped with
bash because OHOS /system/bin/sh (mksh) cannot exec ELF binaries directly.

与 2.74.3 的差异：显式依赖从静态 glib2 改为共享 glib/2.84.0.1.1，与库本体
的 shared-glib 发布形态一致；创建 SoupSession/SoupMessage 会真实实例化
GObject，用于验证单 GObject 副本下不触发 g_param_spec_pool 断言。
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
        # glib 必须显式：libsoup 的公共头文件 include glib/gio/gobject，
        # 而 CMakeDeps 对传递依赖生成空数据（conan 2.29 行为）。版本须与
        # libsoup 链一致：共享 glib/2.84.0.1.1。
        self.requires("glib/2.84.0.1.1", options={"shared": True})

    def generate(self):
        # cmake 是 HNP 工具链二进制，依赖 libc++_shared.so；conan 构建环境把
        # LD_LIBRARY_PATH 覆盖为依赖包 lib 目录，导致 cmake 加载到不兼容
        # libc++（符号缺失 _ZdlPv/_Znwm → Error relocating）。prepend
        # /system/lib64（含可用 libc++_shared.so）。
        self.buildenv_info.prepend_path("LD_LIBRARY_PATH", "/system/lib64")

    def layout(self):
        cmake_layout(self)

    def build(self):
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
