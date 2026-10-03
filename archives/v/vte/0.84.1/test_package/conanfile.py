#!/usr/bin/env python3
"""Conan test_package — vte 0.84.1 (gtk4 flavour).

Consumer E2E (R34): builds test.c against the vte-2.91-gtk4
pkg-config target and runs it on the OHOS host through bash -c with
LD_LIBRARY_PATH injected at the shell level. The test exercises the
no-display surface (version macros, features, VteRegex PCRE2 engine,
substitution) with a full-widget fallback when a display exists.
"""
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class VteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("gtk4/4.22.4")
        self.requires("glib/2.84.0.1.1")
        self.requires("pcre2/10.45")
        self.requires("lz4/1.10.0.1")
        self.requires("fmt/9.1.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        # hnp cmake is an OHOS ELF: needs /system/lib64's
        # libc++_shared.so (gtksourceview5 5.22.0 precedent).
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
            for _p in (_d.cpp_info.libdirs or []):
                if not os.path.isabs(_p) and _base:
                    _p = os.path.join(_base, _p)
                if _p not in libdirs:
                    libdirs.append(_p)
        ldpath = os.pathsep.join(libdirs + ["/system/lib64"])
        exe = os.path.join(self.cpp.build.bindirs[0], "test_vte")
        cmd = (
            "export LD_LIBRARY_PATH=\"{ld}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; "
            "export GDK_BACKEND=broadway; "
            "{exe}"
        ).format(ld=ldpath, exe=shlex.quote(exe))
        self.run(f"{bash} -c '{cmd}'", env="conanrun")
