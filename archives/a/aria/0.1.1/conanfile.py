import os
import shlex

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class AriaConan(ConanFile):
    name = "aria"
    version = "0.1.1"
    description = "Tiny embeddable Lisp-shaped language implemented in C89"
    license = "MIT"
    homepage = "https://github.com/rxi/aria"
    url = ""
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
            filename="aria-0.1.1.tar.gz",
        )

    def build(self):
        apply_conandata_patches(self)

        # The upstream build.sh assumes /bin/bash and gcc. Resolve all build
        # tools from the Conan profile so the recipe is reproducible on OHOS.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")

        compile_cmd = [
            cc,
            "-c",
            "aria.c",
            "-o",
            "aria.o",
            "-O3",
            "-fPIC",
            "-Wall",
            "-Wextra",
            "-std=c89",
            "-pedantic",
        ]
        self.run(shlex.join(compile_cmd), cwd=self.source_folder, env="conanbuild")
        self.run(
            shlex.join([ar, "rcs", "libaria.a", "aria.o"]),
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run(
            shlex.join([ranlib, "libaria.a"]),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "aria.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libaria.a",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["aria"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "aria")
        self.cpp_info.set_property("cmake_target_name", "aria::aria")
