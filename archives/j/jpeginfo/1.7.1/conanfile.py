#!/usr/bin/env python3
"""Conan recipe — jpeginfo 1.7.1 (command-line tool).

jpeginfo prints JPEG file information and integrity checks.
Build system: autotools (configure + make).
Depends on libjpeg.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class JpeginfoConan(ConanFile):
    name = "jpeginfo"
    version = "1.7.1"
    description = "Prints JPEG file information (dimensions, progressive, checksums, integrity check)"
    license = "GPL-3.0"
    homepage = "https://github.com/tjko/jpeginfo"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libjpeg/10")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jpeginfo is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # AutotoolsDeps: feed -I/-L/-l from libjpeg into configure/make
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # Add build folder to include path so config.h is found
        tc.extra_cflags.append(f"-I{self.build_folder}")
        tc.generate()
        # OHOS loader has no default search path for conan-cached shared libs
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # Create subdirectories needed by make for object files
        # (Makefile assumes in-source build, creates .o in md5/, sha256/, sha512/)
        for subdir in ["md5", "sha256", "sha512"]:
            d = os.path.join(self.build_folder, subdir)
            os.makedirs(d, exist_ok=True)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # Copy man page to build dir (Makefile install target expects it there)
        man_src = os.path.join(self.source_folder, "jpeginfo.1")
        man_dst = os.path.join(self.build_folder, "jpeginfo.1")
        if os.path.isfile(man_src) and not os.path.isfile(man_dst):
            import shutil
            shutil.copy2(man_src, man_dst)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
