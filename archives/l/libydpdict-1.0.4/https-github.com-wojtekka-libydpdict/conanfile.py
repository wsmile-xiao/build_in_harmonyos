#!/usr/bin/env python3
"""libydpdict 1.0.4 for HarmonyOS PC (Autotools and Libtool)."""
import os
import runpy

from conan import ConanFile
from conan.tools.build import cross_building, load_toolchain_args
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibydpdictConan(ConanFile):
    name = "libydpdict-1.0.4"
    version = "https-github.com-wojtekka-libydpdict"
    description = "YDP dictionary support library"
    license = "LGPL-2.1"
    homepage = "https://github.com/wojtekka/libydpdict"
    url = "https://github.com/wojtekka/libydpdict"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "*", src=os.path.join(self.recipe_folder, "build_support"),
             dst=os.path.join(self.export_sources_folder, "build_support"))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The release ships Libtool 2.2.6b's ltmain.sh with Libtool 2.4 macros.
        aux_dir = os.path.join(self.source_folder, "_libtool_source")
        get(self, **self.conan_data["libtool_source"], destination=aux_dir)
        copy(self, "libtool-2.4/libltdl/config/ltmain.sh", src=aux_dir,
             dst=self.source_folder, keep_path=False)
        rmdir(self, aux_dir)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The generated header lives in the VPATH build tree.
        tc.extra_cflags.append('-I"{}"'.format(os.path.join(self.build_folder, "include")))
        env = tc.environment()
        # Keep libxml2 optional support disabled: no undeclared host dependency.
        env.define("PKG_CONFIG", "false")
        if self.settings.os == "OHOS":
            # HMDFS does not support GNU Make's parallel jobserver FIFO.
            tc.make_args.append("-j1")
            shim_bin = os.path.join(self.build_folder, "shimbin")
            copy(self, "mktemp", src=os.path.join(self.source_folder, "build_support"),
                 dst=shim_bin)
            os.chmod(os.path.join(shim_bin, "mktemp"), 0o755)
            env.prepend_path("PATH", shim_bin)
        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)
        args = load_toolchain_args(self.generators_folder)["configure_args"]
        # Ensure configure and config.status use the same shell on HarmonyOS.
        self.run('SHELL=/bin/sh CONFIG_SHELL=/bin/sh "{}" {}'.format(
            os.path.join(self.source_folder, "configure"), args))
        autotools = Autotools(self)
        autotools.make()
        # Upstream check_PROGRAMS contains four helpers, but no TESTS runner.
        autotools.make(target="check")
        # misc is listed in DIST_SUBDIRS, but not in the release's SUBDIRS.
        autotools.make(target="check", args=["-C", "misc"])
        if not cross_building(self):
            generate = runpy.run_path(os.path.join(
                self.source_folder, "build_support", "generate_fixtures.py"))["generate"]
            fixture_dir = os.path.join(self.build_folder, "upstream-fixtures")
            generate(fixture_dir)
            for name in ("ydpstress", "ydptest", "ydpxml", "gentable"):
                self.output.info("Running upstream check program: " + name)
                self.run('YDPDICT_TEST_DIR="{}" "{}"'.format(
                    fixture_dir, os.path.join(self.build_folder, "misc", name)))
        else:
            self.output.info("Cross build: upstream helpers compiled; execution requires target device")

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["ydpdict"]
        self.cpp_info.set_property("cmake_file_name", "libydpdict")
        self.cpp_info.set_property("cmake_target_name", "libydpdict::libydpdict")
        self.cpp_info.set_property("pkg_config_name", "libydpdict")
