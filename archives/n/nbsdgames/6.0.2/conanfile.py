#!/usr/bin/env python3
"""Conan recipe — nbsdgames 6.0.2 (Makefile).

Depends on ncurses/6.5 (Conan package) for terminal UI.
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class NbsdgamesConan(ConanFile):
    name = "nbsdgames"
    version = "6.0.2"
    description = "Text-based modern games — a collection of 21 terminal games"
    license = "Public-Domain"
    homepage = "https://github.com/abakh/nbsdgames"
    url = "https://github.com/abakh/nbsdgames"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("ncurses/6.5")

    def validate(self):
        # R32: Use `in ("Linux", "OHOS")` for settings.os check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"nbsdgames supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def _make_arguments(self):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = executables.get("c", "clang")

        # ncurses 依赖的 include/lib 路径显式传入（ncurses 包未安装 .pc 文件，
        # Makefile 的 pkg-config 探测会失败，导致找不到 curses.h）。
        nc_inc = ""
        nc_lib = ""
        nc_libs = ""
        if "ncurses" in self.dependencies:
            nc = self.dependencies["ncurses"]
            pkg = nc.package_folder
            inc_dirs = getattr(nc.cpp_info, "includedirs", None) or []
            lib_dirs = getattr(nc.cpp_info, "libdirs", None) or []
            lib_names = getattr(nc.cpp_info, "libs", None) or []
            nc_inc = " ".join(f"-I{os.path.join(pkg, d)}" for d in inc_dirs)
            nc_lib = " ".join(f"-L{os.path.join(pkg, d)}" for d in lib_dirs)
            nc_libs = " ".join(f"-l{l}" for l in lib_names)

        platform_cflags = "-D_DEFAULT_SOURCE" if str(self.settings.os) == "OHOS" else ""
        widechar_flag = "-DNCURSES_WIDECHAR"

        cflags = " ".join(
            flag
            for flag in [
                platform_cflags,
                widechar_flag,
                nc_inc,
            ]
            if flag
        )

        return {
            "cc": cc,
            "cflags": cflags,
            "libs": f"{nc_lib} {nc_libs}".strip(),
        }

    def build(self):
        apply_conandata_patches(self)
        source_dir = shlex.quote(self.source_folder)
        make_args = self._make_arguments()
        libs_flag = f"LIBS={shlex.quote(make_args['libs'])}" if make_args["libs"] else ""

        self.run(
            " ".join(
                part
                for part in [
                    f"make -C {source_dir}",
                    f"CC={shlex.quote(make_args['cc'])}",
                    f"CFLAGS+={shlex.quote(make_args['cflags'])}",
                    libs_flag,
                    "-j1",
                ]
                if part
            ),
            env="conanbuild",
        )

    def package(self):
        prefix = shlex.quote(self.package_folder)
        source_dir = shlex.quote(self.source_folder)
        make_args = self._make_arguments()
        libs_flag = f"LIBS={shlex.quote(make_args['libs'])}" if make_args["libs"] else ""
        self.run(
            " ".join(
                part
                for part in [
                    f"make -C {source_dir} install",
                    f"CC={shlex.quote(make_args['cc'])}",
                    f"CFLAGS+={shlex.quote(make_args['cflags'])}",
                    libs_flag,
                    f"GAMES_DIR={prefix}/bin",
                    f"SCORES_DIR={prefix}/var/games",
                    f"MAN_DIR={prefix}/share/man",
                ]
                if part
            ),
            env="conanbuild",
        )
        self.run(
            f"make -C {source_dir} manpages MAN_DIR={prefix}/share/man/man6",
            env="conanbuild",
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
