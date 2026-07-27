import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibcrystalhdConan(ConanFile):
    name = "libcrystalhd"
    version = "20130708"
    description = "Broadcom CrystalHD hardware video decoder library (user-space)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/crystalhd/crystalhd"
    url = "https://github.com/crystalhd/crystalhd"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R32: Platform guard
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"libcrystalhd is not supported on {self.settings.os}")
        apply_conandata_patches(self)

        # Build in linux_lib/libcrystalhd subdirectory
        build_dir = os.path.join(self.source_folder, "linux_lib", "libcrystalhd")

        # R33: Get compiler from Conan configuration, not from shell env
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compiler_executables.get("cpp", "clang++")

        # The patched Makefile uses BCGCC for compiler and PREFIX for install paths
        self.run(f"make -C {build_dir} BCGCC={cxx} PREFIX={self.package_folder} -j1")

    def package(self):
        # Install using the Makefile's install target with DESTDIR staging
        # PREFIX="" so files go directly to DESTDIR/lib and DESTDIR/include
        build_dir = os.path.join(self.source_folder, "linux_lib", "libcrystalhd")
        self.run(f"make -C {build_dir} install DESTDIR={self.package_folder} PREFIX=")

        # Fix: headers land in include/libcrystalhd/, libs in lib/
        # Conan expects headers in include/ and libs in lib/

    def package_info(self):
        self.cpp_info.libs = ["crystalhd"]
        # The library installs as libcrystalhd.so.3.6 with symlinks
        self.cpp_info.includedirs = ["include/libcrystalhd"]
