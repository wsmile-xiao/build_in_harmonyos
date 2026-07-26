"""Conan recipe for Neko."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class NekoConan(ConanFile):
    name = "neko"
    version = "2.4.1"
    description = "The Neko virtual machine and compiler"
    license = "MIT"
    homepage = "https://nekovm.org"
    url = "https://github.com/HaxeFoundation/neko"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        for patch in ("boehmgc-0001-ohos-cancel.patch",
                      "boehmgc-0002-ohos-dl-iterate-phdr.patch"):
            copy(
                self,
                patch,
                src=os.path.join(self.recipe_folder, "resources", "boehmgc"),
                dst=os.path.join(self.export_sources_folder, "patches"),
            )

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
            retry=5,
            retry_wait=2,
        )
        get(
            self,
            **self.conan_data["libatomic_ops"],
            destination=os.path.join(
                self.source_folder, "third_party", "libatomic_ops"
            ),
            strip_root=True,
            filename="libatomic_ops-7.6.14.tar.gz",
            retry=5,
            retry_wait=2,
        )
        get(
            self,
            **self.conan_data["bdwgc"],
            destination=os.path.join(self.source_folder, "third_party", "bdwgc"),
            strip_root=True,
            filename="bdwgc-7.6.16.tar.gz",
            retry=5,
            retry_wait=2,
        )
        apply_conandata_patches(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # Neko 2.4.1's CMake does not recognize OHOS as a system name.
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.variables["NEKO_TARGET_OHOS"] = True
        tc.variables["WITH_UI"] = "OFF"
        tc.variables["WITH_MYSQL"] = "OFF"
        tc.variables["WITH_APACHE"] = "OFF"
        tc.variables["WITH_SSL"] = "OFF"
        tc.variables["WITH_SQLITE"] = "OFF"
        tc.variables["WITH_REGEXP"] = "OFF"
        tc.variables["WITH_NEKOML"] = "OFF"
        tc.variables["RUN_LDCONFIG"] = "OFF"
        tc.variables["RELOCATABLE"] = "OFF"
        tc.variables["NEKO_JIT_DISABLE"] = "ON"
        tc.variables["STATIC_DEPS"] = "BoehmGC"
        tc.cache_variables["ZLIB_ROOT"] = self.dependencies["zlib"].package_folder
        tc.generate()

    def build(self):
        for patch in ("boehmgc-0001-ohos-cancel.patch",
                      "boehmgc-0002-ohos-dl-iterate-phdr.patch"):
            copy(
                self,
                patch,
                src=os.path.join(self.export_sources_folder, "patches"),
                dst=os.path.join(self.build_folder, "patches"),
            )
        cmake = CMake(self)
        cmake.configure()
        # Homebrew deparallelizes Neko because its bootstrap rules share outputs.
        self.conf.define("tools.build:jobs", 1)
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "OHOS":
            self._sign_package_elfs()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _sign_package_elfs(self):
        import glob

        patterns = (
            os.path.join(self.package_folder, "bin", "*"),
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
            os.path.join(self.package_folder, "lib", "**", "*.ndll"),
        )
        files = {
            path
            for pattern in patterns
            for path in glob.glob(pattern, recursive=True)
            if os.path.isfile(path) and not os.path.islink(path)
        }
        objcopy = shutil.which("llvm-objcopy")
        signer = shutil.which("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "OHOS ELF signing requires llvm-objcopy and binary-sign-tool "
                "on PATH"
            )
        for path in sorted(files):
            self.run(
                f'"{objcopy}" --remove-section .codesign "{path}"',
                ignore_errors=False,
            )
            self.run(
                f'"{signer}" sign -inFile "{path}" -outFile "{path}" '
                "-selfSign 1",
                ignore_errors=False,
            )

    def package_info(self):
        self.cpp_info.libs = ["neko"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "neko")
        self.cpp_info.set_property("cmake_target_name", "neko::neko")
