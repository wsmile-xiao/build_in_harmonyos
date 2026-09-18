#!/usr/bin/env python3
"""Conan recipe for libva 2.22.0 — Video Acceleration API library."""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class LibvaConan(ConanFile):
    name = "libva"
    version = "2.22.0"
    description = "Video Acceleration API library, provides video decode/encode acceleration support"
    license = "MIT"
    homepage = "https://github.com/intel/libva"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libdrm/2.4.133")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["with_x11"] = "no"
        tc.project_options["with_glx"] = "no"
        tc.project_options["with_wayland"] = "no"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["build.pkg_config_path"] = self.generators_folder
        tc.generate()
        pkg_config_deps = PkgConfigDeps(self)
        pkg_config_deps.generate()
        tc = VirtualBuildEnv(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        os.environ["AR"] = "/data/service/hnp/bin/llvm-ar"
        os.environ["NM"] = "/data/service/hnp/bin/llvm-nm"
        os.environ["RANLIB"] = "/data/service/hnp/bin/llvm-ranlib"
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # Install-time rpath patching ($ORIGIN -> XXXXXXXX) modifies the ELF
        # bytes of libva-drm.so after linking, which invalidates the
        # linker-generated .codesign page hashes. OHOS requires a valid code
        # signature for dlopen/mmap PROT_EXEC, so the libraries must be
        # re-signed after install (see knowledge E489).
        if self.settings.os == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool):
                for lib in glob.glob(os.path.join(self.package_folder, "lib", "*.so.*")):
                    if os.path.isfile(lib) and not os.path.islink(lib):
                        self.run(f'"{sign_tool}" sign -inFile "{lib}" '
                                 f'-outFile "{lib}" -selfSign 1', env="conanbuild")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Libva")
        self.cpp_info.set_property("pkg_config_name", "libva")

        va = self.cpp_info.components["va"]
        va.libs = ["va"]
        va.set_property("pkg_config_name", "libva")

        va_drm = self.cpp_info.components["va-drm"]
        va_drm.libs = ["va-drm"]
        va_drm.set_property("pkg_config_name", "libva-drm")
        va_drm.requires = ["va"]
