#!/usr/bin/env python3
"""Conan application recipe for virt-what 1.27."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class VirtWhatConan(ConanFile):
    name = "virt-what"
    version = "1.27"
    description = "Detects whether the system is running in a virtual machine"
    license = "GPL-2.0-or-later"
    homepage = "https://people.redhat.com/~rjones/virt-what/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"virt-what supports Linux and HarmonyOS, not {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The upstream package has no third-party build or runtime dependencies.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Conan stages DESTDIR into package_folder, so install paths are
        # expressed relative to / and land directly in package_folder/bin.
        # Upstream splits the script/helper/program across sbin and libexec.
        tc.configure_args.extend(
            [
                "--bindir=/bin",
                "--sbindir=/bin",
                "--libexecdir=/bin",
            ]
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            os.umask(0o022)

        # basic_layout copies the sources into this package-specific writable
        # tree. The upstream fixture scripts use paths relative to the source
        # directory, so configure and test in that tree instead of nesting a
        # second copy under Conan's build folder.
        build_root = self.source_folder

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            ["--bindir=/bin", "--sbindir=/bin", "--libexecdir=/bin"]
        )
        configure_args = " ".join(shlex.quote(arg) for arg in tc.configure_args)
        shell = "/bin/sh" if str(self.settings.os) == "OHOS" else "sh"
        logical_pwd = os.path.abspath(build_root)
        self.run(
            f"CONFIG_SHELL={shlex.quote(shell)} SHELL={shlex.quote(shell)} "
            f"PWD={shlex.quote(logical_pwd)} {shlex.quote(shell)} ./configure "
            f"{configure_args}",
            cwd=build_root,
            env="conanbuild",
        )
        # Run every upstream fixture against this same tree (R51).
        self.run("make -j1 check", cwd=build_root, env="conanbuild")

    def package(self):
        build_root = self.source_folder
        self.run(
            f'make install DESTDIR="{self.package_folder}"',
            cwd=build_root,
            env="conanbuild",
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        for program in ("virt-what", "virt-what-cvm", "virt-what-cpuid-helper"):
            path = os.path.join(self.package_folder, "bin", program)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
