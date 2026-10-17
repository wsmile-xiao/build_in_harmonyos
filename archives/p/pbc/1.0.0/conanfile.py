#!/usr/bin/env python3
"""Conan recipe — PBC 1.0.0 (Autotools)."""

import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PbcConan(ConanFile):
    name = "pbc"
    version = "1.0.0"
    description = "Pairing-Based Cryptography library"
    license = "LGPL-3.0-or-later OR Apache-2.0"
    homepage = "https://crypto.stanford.edu/pbc/"
    url = "https://crypto.stanford.edu/pbc/download.html"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "gmp/6.3.0",
            transitive_headers=True,
            transitive_libs=True,
        )

    def build_requirements(self):
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("bison/3.8.2")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["test_sources"]["googletest"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "googletest"),
        )

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append("--enable-cxx")
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])

        gmp = self.dependencies["gmp"].cpp_info
        flex = self.dependencies.build["flex"].cpp_info
        environment = toolchain.environment()
        environment.prepend("CPPFLAGS", "-I{}".format(gmp.includedirs[0]))
        environment.prepend(
            "LDFLAGS",
            "-L{} -L{}".format(gmp.libdirs[0], flex.libdirs[0]),
        )
        toolchain.generate(environment)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        autotools.make(target="check", args=["VERBOSE=1"])
        self.run("./gtest --gtest_brief=1")
        self.run("./pbc_test --gtest_brief=1")

    def package(self):
        Autotools(self).install()
        for archive in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(archive)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE-2.0.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        if str(self.settings.os) != "OHOS":
            return
        signer = shutil.which("binary-sign-tool")
        if not signer:
            self.output.info("binary-sign-tool is unavailable; package remains unsigned")
            return
        for path in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            output = path + ".signed"
            result = subprocess.run(
                [
                    signer,
                    "sign",
                    "-selfSign",
                    "1",
                    "-signAlg",
                    "SHA256withECDSA",
                    "-inFile",
                    path,
                    "-outFile",
                    output,
                ],
                capture_output=True,
                check=False,
                timeout=60,
            )
            if result.returncode != 0 or not os.path.isfile(output):
                raise RuntimeError("failed to sign {}".format(path))
            shutil.copymode(path, output)
            os.replace(output, path)

    def package_info(self):
        self.cpp_info.libs = ["pbc"]
        self.cpp_info.set_property("cmake_file_name", "pbc")
        self.cpp_info.set_property("cmake_target_name", "pbc::pbc")
        self.cpp_info.set_property("pkg_config_name", "pbc")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
