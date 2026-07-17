#!/usr/bin/env python3
"""Conan recipe for ncurses 6.5 — OHOS static build."""

import os

from conan import ConanFile
from conan.tools.files import get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.5"
    description = "The ncurses (new curses) library"
    license = "X11"
    homepage = "https://www.gnu.org/software/ncurses"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--without-shared")
        tc.configure_args.append("--without-debug")
        tc.configure_args.append("--without-ada")
        tc.configure_args.append("--without-manpages")
        tc.configure_args.append("--without-tests")
        tc.configure_args.append("--without-cxx-binding")
        tc.configure_args.append("--enable-widec")
        tc.configure_args.append("--enable-overwrite")
        tc.generate()

    def build(self):
        replace_in_file(
            self,
            os.path.join(self.source_folder, "config.guess"),
            """    *:Minix:*:*)
	GUESS=$UNAME_MACHINE-unknown-minix
	;;""",
            """    *:Minix:*:*)
	GUESS=$UNAME_MACHINE-unknown-minix
	;;
    *:HarmonyOS:*:*)
	case "$UNAME_MACHINE" in
	    aarch64|arm64)
		MACHINE=aarch64
		;;
	    armv7*|armv8*)
		MACHINE=arm
		;;
	    x86_64|amd64)
		MACHINE=x86_64
		;;
	    i?86)
		MACHINE=i686
		;;
	    *)
		MACHINE="$UNAME_MACHINE"
		;;
	esac
	GUESS=${MACHINE}-unknown-linux-ohos
	;;""",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "config.sub"),
            "| fiwix* | mlibc* | cos* | mbr* | ironclad* )",
            "| fiwix* | mlibc* | cos* | mbr* | ironclad* | ohos* )",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "config.sub"),
            "| linux-relibc*- | linux-uclibc*- )",
            "| linux-relibc*- | linux-uclibc*- | linux-ohos*- )",
        )

        autotools = Autotools(self)
        autotools.configure()
        # OHOS HMDFS noexec (E046): config.status 中临时 awk 脚本无法直接执行
        self.run(
            r"sed -i 's|\./conf[^/]*/subs1\.awk|$AWK -f &|g' config.status",
            cwd=self.source_folder,
            ignore_errors=True,
        )
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ncursesw", "panelw", "menuw", "formw"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "ncursesw")
