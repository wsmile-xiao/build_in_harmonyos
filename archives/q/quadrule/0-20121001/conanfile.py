#!/usr/bin/env python3
"""Conan recipe — quadrule 0-20121001 (Autotools)."""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class QuadruleConan(ConanFile):
    name = "quadrule"
    version = "0-20121001"
    description = "Quadrature rules and numerical integration routines"
    license = "LGPL-3.0-or-later"
    homepage = "https://people.math.sc.edu/Burkardt/c_src/quadrule/quadrule.html"
    url = "https://salsa.debian.org/science-team/quadrule"
    topics = ("quadrature", "numerical-integration", "mathematics")
    package_type = "library"
    implements = ["auto_shared_fpic"]

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("quadrule supports Linux and OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def _make_config_status_tmp_writable(self):
        if self.settings.os != "OHOS":
            return
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(
            self,
            configure,
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`(mktemp -d "./confXXXXXX") 2>/dev/null`',
        )
        replace_in_file(
            self,
            configure,
            '(umask 077 && mkdir "$tmp")',
            '(mkdir "$tmp")',
        )

    def build(self):
        apply_conandata_patches(self)
        self._make_config_status_tmp_writable()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # The snapshot registers no upstream tests, but invoking the official
        # target preserves that contract and catches future source changes.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install(args=["-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        for libtool_file in glob.glob(
            os.path.join(self.package_folder, "lib", "*.la")
        ):
            os.remove(libtool_file)

    def package_info(self):
        self.cpp_info.libs = ["quadrule"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "quadrule")
        self.cpp_info.set_property("cmake_target_name", "quadrule::quadrule")
        self.cpp_info.set_property("pkg_config_name", "quadrule")
