import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibxsmmConan(ConanFile):
    name = "libxsmm"
    version = "1.17"
    description = "Library for specialized small matrix operations"
    license = "BSD-3-Clause"
    homepage = "https://github.com/libxsmm/libxsmm"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("libxsmm/1.17 supports OHOS armv8 only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _make_args(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        ar = compilers.get("ar") or "llvm-ar"
        ranlib = compilers.get("ranlib") or "llvm-ranlib"
        return (
            f'CC="{cc}" CXX="{cxx}" AR="{ar}" RANLIB="{ranlib}" '
            "FC= PLATFORM=1 JIT=0 BLAS=0 STATIC=1 COMPATIBLE=1"
        )

    def build(self):
        apply_conandata_patches(self)
        make_args = self._make_args()
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        bash_dir = os.path.dirname(bash)
        tmpdir = os.path.join(self.build_folder, "tmp")
        self.run(f'mkdir -p "{tmpdir}"', cwd=self.build_folder)
        make_env = (
            f'PATH="{bash_dir + ":" if bash_dir else ""}$PATH" TMPDIR="{tmpdir}" '
            f'SHELL="{bash}"'
        )
        self.run(f"{make_env} make -j1 {make_args}", cwd=self.source_folder)
        self.run(f"{make_env} make -j1 {make_args} tests", cwd=self.source_folder)

    def package(self):
        copy(
            self,
            "libxsmm*.a",
            os.path.join(self.source_folder, "lib"),
            os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "libxsmm*.h",
            os.path.join(self.source_folder, "include"),
            os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE.md",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["xsmm", "xsmmnoblas"]
        self.cpp_info.system_libs = ["dl", "m", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "libxsmm")
        self.cpp_info.set_property("cmake_target_name", "libxsmm::libxsmm")
        self.cpp_info.set_property("pkg_config_name", "libxsmm")
