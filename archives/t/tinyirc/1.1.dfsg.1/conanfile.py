"""Conan recipe for the tinyirc 1.1.dfsg.1 terminal client."""

import os
import shlex

from conan import ConanFile
from conan.tools.files import copy, get, patch
from conan.tools.layout import basic_layout


class TinyircConan(ConanFile):
    name = "tinyirc"
    version = "1.1.dfsg.1"
    description = "Small terminal IRC client"
    homepage = "https://github.com/nlaredo/tinyirc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "GPL-2.0-only"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def requirements(self):
        self.requires("ncurses/6.6", run=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        patch(
            self,
            base_path=self.source_folder,
            patch_file=os.path.join(
                self.export_sources_folder, "patches", "0001-passwd-optional-utmp.patch"
            ),
        )

    def build(self):
        ncurses = self.dependencies["ncurses"].cpp_info
        compiler = self.conf.get("tools.build:compiler_executables", default={}).get(
            "c", "cc"
        )
        flags = " ".join(
            [
                "-O2",
                "-fPIC",
                "-std=gnu89",
                "-DPOSIX",
                "-Dhline=tinyirc_hline",
                "-Dtimeout=tinyirc_timeout",
                "-I" + ncurses.includedirs[0],
            ]
        )
        self.run(
            "make -B -j1 -C {} tinyirc CC={} CFLAGS={} LDFLAGS={} "
            "LIBS=-lncursesw SERVER=127.0.0.1 PORT=6667".format(
                shlex.quote(self.source_folder),
                shlex.quote(compiler),
                shlex.quote(flags),
                shlex.quote("-L" + ncurses.libdirs[0]),
            )
        )

    def package(self):
        copy(
            self,
            "tinyirc",
            self.source_folder,
            os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
