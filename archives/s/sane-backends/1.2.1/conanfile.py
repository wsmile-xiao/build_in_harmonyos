#!/usr/bin/env python3
"""Conan recipe for the portable SANE core on OpenHarmony."""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    replace_in_file,
)
from conan.tools.build import can_run
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps


class SaneBackendsConan(ConanFile):
    name = "sane-backends"
    version = "1.2.1"
    description = "Scanner Access Now Easy backend libraries and command-line tools"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/sane-project/backends"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The source archive requires Autotools bootstrap; CI workers do not provide aclocal.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        self.requires("libusb/1.0.27")
        self.requires("libjpeg/10")
        self.requires("libpng/1.6.58")
        self.requires("libtiff/4.7.2")
        self.requires("curl/8.15.0")
        self.requires("libxml2/2.15.3")

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("sane-backends is currently supported only for OHOS armv8")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)


    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # The regenerated upstream config.guess does not recognize HarmonyOS.
        tc.configure_args.extend([
            "--build=aarch64-linux-gnu",
            "--host=aarch64-linux-ohos",
        ])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        replace_in_file(
            self,
            os.path.join(self.build_folder, "backend/Makefile.am"),
            "libsane_la_LIBADD = $(COMMON_LIBS) \\\n    $(PRELOADABLE_BACKENDS_ENABLED) libdll_preload.la \\\n    sane_strstatus.lo",
            "libsane_la_LIBADD = $(COMMON_LIBS) \\\n    libdll.la \\\n    $(PRELOADABLE_BACKENDS_ENABLED) \\\n    sane_strstatus.lo",
        )
        autotools = Autotools(self)
        bootstrap_env = Environment()
        automake_bin = os.path.join(self.dependencies.build["automake"].package_folder, "bin")
        libtool_bin = os.path.join(self.dependencies.build["libtool"].package_folder, "bin")
        bootstrap_env.prepend_path("PATH", automake_bin)
        bootstrap_env.prepend_path("PATH", libtool_bin)
        pkg_m4_matches = glob.glob(
            os.path.join(
                os.environ.get("HNP_ROOT", "/data/service/hnp"),
                "pkg-config.org",
                "pkg-config_*",
                "share",
                "aclocal",
                "pkg.m4",
            )
        )
        if not pkg_m4_matches:
            raise ConanInvalidConfiguration("pkg.m4 is required to regenerate the Autotools build system")
        pkg_m4 = os.path.dirname(pkg_m4_matches[0])
        bootstrap_env.define("ACLOCAL_PATH", pkg_m4)
        bootstrap_env.define("AUTOCONF", shutil.which("autoconf") or "autoconf")
        bootstrap_env.define("AUTOM4TE", shutil.which("autom4te") or "autom4te")
        bootstrap_env.define("M4", shutil.which("m4") or "m4")
        libtoolize = shutil.which("libtoolize") or "libtoolize"
        shell = shutil.which("bash") or shutil.which("sh") or "sh"
        bootstrap_env.define("LIBTOOLIZE", f"{shell} {libtoolize}")
        with bootstrap_env.vars(self).apply():
            self.run(f"aclocal --force -I m4 -I {pkg_m4}", cwd=self.build_folder)
            self.run("autoheader -I m4", cwd=self.build_folder)
            self.run("automake --add-missing --copy --force-missing", cwd=self.build_folder)
        configure = os.path.join(self.build_folder, "configure")
        replace_in_file(
            self,
            configure,
            '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status',
            '{ test "$ac_tmp" = . || { test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; }; } && exit $exit_status',
        )
        replace_in_file(self, configure, "ac_tmp=$tmp", "ac_tmp=.")
        replace_in_file(self, configure, "ac_stdint=$tmp/_stdint.h", "ac_stdint=./_stdint.h")
        env = Environment()
        env.define("BACKENDS", "test genesys")
        env.define("PRELOADABLE_BACKENDS", "")
        env.define("SHELL", "/bin/sh")
        env.define("CONFIG_SHELL", "/bin/sh")
        with env.vars(self).apply():
            try:
                autotools.configure()
            except ConanException:
                config_log = os.path.join(self.build_folder, "config.log")
                if os.path.isfile(config_log):
                    lines = load(self, config_log).splitlines()
                    marker_index = next(
                        (index for index, line in enumerate(lines)
                         if "checking whether the C compiler works" in line),
                        0,
                    )
                    diagnostic = "\n".join(lines[marker_index:marker_index + 35])
                    self.output.error("configure compiler diagnostic:\n" + diagnostic)
                raise
            autotools.make(args=["-j1"])
            if self.settings.os == "OHOS":
                self.run(
                    "make -j1 -C testsuite/sanei sanei_usb_test test_wire "
                    "sanei_check_test sanei_config_test sanei_constrain_test",
                    cwd=self.build_folder,
                )
                self.run("make -j1 -C backend libgenesys.la", cwd=self.build_folder)
                self.run("make -j1 -C testsuite/backend/genesys genesys_unit_tests", cwd=self.build_folder)
                self.run("make -j1 -C tools sane-desc", cwd=self.build_folder)
            elif not self.conf.get("tools.build:skip_test", default=False):
                self.run("make -j1 check", cwd=self.build_folder)

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.libs = ["sane"]
        self.cpp_info.bindirs = ["bin", "sbin"]
