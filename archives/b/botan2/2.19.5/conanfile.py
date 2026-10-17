import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class Botan2Conan(ConanFile):
    name = "botan2"
    version = "2.19.5"
    package_type = "library"
    description = "Botan 2 C++ cryptography library"
    license = "BSD-2-Clause"
    homepage = "https://botan.randombits.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("cryptography", "security", "tls", "hash")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"botan2 is adapted for Linux/OHOS, got {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"botan2/2.19.5 is validated for OHOS armv8, got {self.settings.arch}"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration("botan2/2.19.5 is packaged as a static library")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return executables.get("cpp", "c++")

    def build(self):
        apply_conandata_patches(self)
        configure = (
            f'"{sys.executable}" "{os.path.join(self.source_folder, "configure.py")}" '
            f"--cc=clang --cc-bin=\"{self._compiler()}\" --os=linux --cpu=arm64 "
            f"--prefix=\"{self.package_folder}\" --build-targets=static,tests"
        )
        self.run(configure, cwd=self.build_folder)
        self.run("make -j1", cwd=self.build_folder)
        self.run("make -j1 check", cwd=self.build_folder)
        # Botan's Makefile invokes 'ar crs libbotan-2.a <all .o>' as a single
        # ~13 KB command line. OHOS toybox shell silently truncates it, so the
        # archive is never produced. Recreate it with a glob (short command).
        if not os.path.isfile(os.path.join(self.build_folder, "libbotan-2.a")):
            self.run("rm -f libbotan-2.a && ar crs libbotan-2.a build/obj/lib/*.o",
                     cwd=self.build_folder)

    def package(self):
        # configure.py / make run with cwd=self.build_folder, so the static
        # archive lands in build_folder root (not build_folder/lib).
        copy(self, "libbotan-2*.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        # Botan's configure.py generates symlinks for headers. conan's copy()
        # preserves symlinks, which break once src/ is absent from the package.
        # Use shutil.copytree with follow_symlinks=True to dereference them.
        import shutil
        shutil.copytree(
            os.path.join(self.build_folder, "build", "include"),
            os.path.join(self.package_folder, "include"),
            symlinks=False,
            dirs_exist_ok=True,
        )
        copy(self, "license.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["botan-2"]
        self.cpp_info.set_property("cmake_file_name", "botan2")
        self.cpp_info.set_property("cmake_target_name", "botan2::botan2")
        self.cpp_info.set_property("pkg_config_name", "botan-2")
