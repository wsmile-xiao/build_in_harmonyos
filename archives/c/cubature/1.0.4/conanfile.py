#!/usr/bin/env python3
"""Conan recipe — cubature 1.0.4 (CMake)."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class CubatureConan(ConanFile):
    name = "cubature"
    version = "1.0.4"
    description = "Adaptive multidimensional integration of vector-valued functions"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/stevengj/cubature"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        toolchain.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if can_run(self):
            library = os.path.join(self.build_folder, "libcubature.so")
            htest = os.path.join(self.build_folder, "htest")
            ptest = os.path.join(self.build_folder, "ptest")
            if str(self.settings.os) == "OHOS":
                for path in (library, htest, ptest):
                    self._sign_ohos_elf(path)

            test_environment = Environment()
            test_environment.prepend_path("LD_LIBRARY_PATH", self.build_folder)
            with test_environment.vars(self).apply():
                for executable in (htest, ptest):
                    self.run(
                        f'"{executable}" 3 1e-2 "0/1/2/3/4/5/6/7" 1000000',
                        env=["conanbuild", "conanrun"],
                    )
                    self.run(
                        f'"{executable}" 3 1e-8 8 1000000',
                        env=["conanbuild", "conanrun"],
                    )
        else:
            self.output.warning("Target upstream tests are not runnable in this build context")

    def package(self):
        CMake(self).install()
        copy(
            self,
            "COPYING.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(
                os.path.join(self.package_folder, "lib", "libcubature.so")
            )

    def package_info(self):
        self.cpp_info.libs = ["cubature"]
        self.cpp_info.set_property("cmake_file_name", "cubature")
        self.cpp_info.set_property("cmake_target_name", "cubature::cubature")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    @staticmethod
    def _sign_ohos_elf(path):
        if not os.path.isfile(path):
            raise ConanException(f"Missing OHOS ELF for signing: {path}")
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanException("Required OHOS signing tools are missing")
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=True,
            timeout=30,
        )
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                path,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
        os.chmod(path, (os.stat(path).st_mode & 0o777) | 0o055)
