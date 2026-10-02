#!/usr/bin/env python3
"""Conan recipe for the xva-img 1.5 command-line application."""

import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class XvaImgConan(ConanFile):
    name = "xva-img"
    version = "1.5"
    description = "Create and extract virtual disk images from Citrix XVA files"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/eriklax/xva-img"
    url = "https://github.com/eriklax/xva-img"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.8.1")
        self.requires("xxhash/0.8.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_executable(os.path.join(self.package_folder, "bin", "xva-img"))

    def _sign_ohos_executable(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanException("OHOS package signing requires binary-sign-tool")
        if not os.path.isfile(objcopy):
            raise ConanException("OHOS package signing requires llvm-objcopy")

        # Remove the SDK placeholder signature before inserting the real signature.
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        signed = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            check=True,
        )
        os.replace(signed, path)
        os.chmod(
            path,
            stat.S_IMODE(os.stat(path).st_mode)
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH,
        )

    def package_info(self):
        # R38: expose only the actual command-line application directory.
        self.cpp_info.bindirs = ["bin"]
