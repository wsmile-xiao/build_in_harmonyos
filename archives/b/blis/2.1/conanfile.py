import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BlisConan(ConanFile):
    name = "blis"
    version = "2.1"
    description = "BLAS-like Library Instantiation Software framework"
    license = "BSD-3-Clause"
    homepage = "https://github.com/flame/blis"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("blis/2.1 supports OHOS armv8 only")
        if self.options.shared:
            raise ConanInvalidConfiguration("blis/2.1 is packaged as a static library on OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "llvm-ar"
        ranlib = compilers.get("ranlib") or "llvm-ranlib"
        configure = (
            f'CC="{cc}" AR="{ar}" RANLIB="{ranlib}" "{bash}" ./configure '
            f'--prefix="{self.package_folder}" --libdir="{self.package_folder}/lib" '
            f'--includedir="{self.package_folder}/include" --disable-shared --enable-cblas '
            "--disable-threading arm64"
        )
        self.run(configure, cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)
        self.run("make check -j1", cwd=self.source_folder)

    def package(self):
        copy(
            self,
            "libblis.a",
            os.path.join(os.path.dirname(self.build_folder), "lib", "arm64"),
            os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "*.h",
            os.path.join(self.source_folder, "include"),
            os.path.join(self.package_folder, "include"),
            keep_path=True,
        )
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["blis"]
        self.cpp_info.includedirs = ["include", "include/arm64"]
        self.cpp_info.set_property("cmake_file_name", "BLIS")
        self.cpp_info.set_property("cmake_target_name", "BLIS::BLIS")
        self.cpp_info.set_property("pkg_config_name", "blis")
        self.cpp_info.system_libs = ["m", "pthread"]
