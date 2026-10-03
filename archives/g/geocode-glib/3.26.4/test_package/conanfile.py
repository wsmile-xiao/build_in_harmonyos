#!/usr/bin/env python3
"""Conan test_package — geocode-glib 3.26.4.

Consumer E2E (R34): builds a C consumer against the geocode-glib-2.0
pkg-config target and runs it on the OHOS host through bash -c with
LD_LIBRARY_PATH injected at the shell level. Pure-logic API surface
(location round-trips, distance, geo URI parsing) — no network needed.
"""
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import Environment


class GeocodeGlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Align with the main recipe's dependency line (glib/2.84.0 +
        # json-glib/1.6.6 + libsoup/3.6.5-r1 share the published graph).
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        self.requires("json-glib/1.10.6")
        self.requires("libsoup3/3.6.5-r3")

    def layout(self):
        cmake_layout(self)

    def build(self):
        # hnp cmake is an OHOS ELF: needs /system/lib64's libc++_shared.so
        # (gtksourceview5 5.22.0 precedent).
        os.environ["LD_LIBRARY_PATH"] = (
            "/system/lib64" + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        libdirs = []
        for _r, _d in self.dependencies.items():
            _base = getattr(_d, "package_folder", None) or ""
            # components 形式的 package_info 顶层 libdirs 为空（json-glib
            # 1.10.6 现行修订先例），组件 libdirs 一并聚合。
            _dirs = list(_d.cpp_info.libdirs or [])
            try:
                for _comp in (_d.cpp_info.components or {}).values():
                    _dirs += list(getattr(_comp, "libdirs", []) or [])
            except Exception:
                pass
            for _p in _dirs:
                if not os.path.isabs(_p) and _base:
                    _p = os.path.join(_base, _p)
                if _p not in libdirs:
                    libdirs.append(_p)
        ldpath = os.pathsep.join(libdirs)
        exe = os.path.join(self.cpp.build.bindirs[0], "test_geocode_glib")
        cmd = (
            "export LD_LIBRARY_PATH=\"{ld}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; "
            "{exe}"
        ).format(ld=ldpath, exe=shlex.quote(exe))
        self.run(f"{bash} -c '{cmd}'", env="conanrun")
