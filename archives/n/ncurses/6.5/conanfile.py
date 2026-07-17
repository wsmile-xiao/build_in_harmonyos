#!/usr/bin/env python3
"""Conan recipe for ncurses 6.5 — OHOS static build."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
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

    def export_sources(self):
        export_conandata_patches(self)

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
        apply_conandata_patches(self)
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
