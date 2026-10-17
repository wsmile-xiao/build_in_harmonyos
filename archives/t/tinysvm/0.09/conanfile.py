#!/usr/bin/env python3
"""Conan 2 recipe for TinySVM 0.09 on HarmonyOS PC."""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class TinySVMConan(ConanFile):
    name = "tinysvm"
    version = "0.09"
    description = "Small C++ support vector machine library and command-line toolkit"
    license = "LGPL-2.0-or-later"
    homepage = "http://www.chasen.org/~taku/software/TinySVM/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tinysvm is supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        # This old autotools release is built in source, matching upstream.
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # GCC 15 rejects an implicit-int probe in the 2002 configure script;
        # the source itself is C89. Clang 15 on HarmonyOS accepts this too.
        tc.extra_cflags.append("-std=gnu89")
        tc.extra_cxxflags.append("-std=gnu++98")
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _shell(self):
        for name in ("bash", "sh"):
            shell = shutil.which(name)
            if shell:
                return shell
        raise ConanInvalidConfiguration("bash or sh is required to run configure")

    def build(self):
        apply_conandata_patches(self)
        shell = self._shell()
        source = self.source_folder.replace("\\", "/")
        prefix = self.package_folder.replace("\\", "/")
        self.run(
            f"cd '{source}' && CONFIG_SHELL='{shell}' '{shell}' "
            f"./configure --prefix='{prefix}'",
            env="conanbuild",
        )
        jobs = 1 if str(self.settings.os) == "OHOS" else (os.cpu_count() or 1)
        self.run(
            f"cd '{source}' && make -j{jobs}",
            env="conanbuild",
        )
        if can_run(self):
            # Upstream inventory: test.sh through test5.sh, all mandatory.
            self.run(f"cd '{source}' && make check", env="conanbuild")
        else:
            self.output.warning("cross-build: five upstream tests were skipped")

    def package(self):
        shell = self._shell()
        source = self.source_folder.replace("\\", "/")
        self.run(
            f"cd '{source}' && CONFIG_SHELL='{shell}' make install",
            env="conanbuild",
        )
        for libtool_archive in glob.glob(
            os.path.join(self.package_folder, "lib", "*.la")
        ):
            os.remove(libtool_archive)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tinysvm")
        self.cpp_info.set_property("cmake_target_name", "tinysvm::tinysvm")
        self.cpp_info.set_property("pkg_config_name", "tinysvm")
        self.cpp_info.libs = ["tinysvm"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
