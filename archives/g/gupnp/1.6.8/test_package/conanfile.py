#!/usr/bin/env python3
"""Conan test_package for gupnp 1.6.8 — Conan L1 official test.

Builds test_gupnp.c (real GUPnP API: GUPnPContext creation on loopback +
server/session accessors + default-language) with CMake (CMakeDeps +
CMakeToolchain) and runs it. The binary is wrapped with bash because
OHOS /system/bin/sh (mksh) cannot exec ELF binaries directly.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GupnpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # 显式列出 generators 会替换 conan 默认集，必须带上 VirtualRunEnv /
    # VirtualBuildEnv：漏了它们 test() 里 env="conanrun" 就拿不到 conanrun
    # 环境的 LD_LIBRARY_PATH（libsoup3/gssdp 同款实撞）。
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # glib2 必须显式声明：gupnp 公共头 include glib/gio/gobject，且
        # CMakeDeps 对传递依赖生成空数据（libsoup3/gssdp 同款记录）。libsoup3 /
        # gssdp / libxml2 同理显式声明——gupnp 是 shared 库，运行时 NEEDED
        # libsoup-3.0.so、libgssdp-1.6.so、libxml2.so，必须让 conan 解析出
        # 各自 package_folder 才能拼 LD_LIBRARY_PATH。
        self.requires("glib2/2.88.0")
        self.requires("libsoup3/3.6.5-r1")
        self.requires("gssdp/1.6.6")
        self.requires("libxml2/2.15.3")

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
        # 收集全部依赖（含传递的 glib2/libsoup3/gssdp/libxml2 及其传递依赖）
        # 的 libdirs，拼成 LD_LIBRARY_PATH（不能只依赖 conanrun——见 libsoup3
        # 实撞记录）。
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
            f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_gupnp'",
            env="conanrun")
