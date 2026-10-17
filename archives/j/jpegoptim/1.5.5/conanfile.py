#!/usr/bin/env python3
"""Conan recipe — jpegoptim 1.5.5 (command-line JPEG optimizer).

jpegoptim optimizes/compresses JPEG files. Build system: CMake.
Depends on libjpeg. LIBJPEG_INCLUDE_DIR/LIBJPEG_LIBRARY are passed
explicitly to CMake: the upstream default USE_MOZJPEG=1 would otherwise
download and build MozJPEG at build time (unusable offline).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JpegoptimConan(ConanFile):
    name = "jpegoptim"
    version = "1.5.5"
    description = "Utility to optimize/compress JPEG files losslessly or to a given maximum quality"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/tjko/jpegoptim"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libjpeg/10")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jpegoptim is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        dep = self.dependencies["libjpeg"]
        incdir = dep.cpp_info.includedirs[0]
        libfile = None
        for d in dep.cpp_info.libdirs:
            # prefer the linker symlink, then any shared/static variant
            for pattern in ("libjpeg.so", "libjpeg.a", "libjpeg.so.*"):
                hits = sorted(glob.glob(os.path.join(d, pattern)))
                if hits:
                    libfile = hits[0]
                    break
            if libfile:
                break
        if libfile is None:
            raise ConanInvalidConfiguration(
                "libjpeg library file not found in dependency package"
            )
        # Upstream CMake: custom libjpeg paths disable the vendored
        # MozJPEG download/build (USE_MOZJPEG). Both set explicitly.
        tc.variables["LIBJPEG_INCLUDE_DIR"] = incdir
        tc.variables["LIBJPEG_LIBRARY"] = libfile
        tc.variables["USE_MOZJPEG"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Upstream CMakeLists.txt has no install() rules; copy the built
        # binary into the package manually.
        candidates = [
            os.path.join(self.build_folder, "jpegoptim"),
            os.path.join(self.build_folder, str(self.settings.build_type), "jpegoptim"),
        ]
        bin_src = next((p for p in candidates if os.path.isfile(p)), None)
        if bin_src is None:
            raise ConanInvalidConfiguration(
                f"jpegoptim binary not found in build folder {self.build_folder}"
            )
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        out = os.path.join(bindir, "jpegoptim")
        shutil.copy2(bin_src, out)
        os.chmod(out, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
