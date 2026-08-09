#!/usr/bin/env python3
"""Conan recipe for ImageMagick-full 7.1.2-23 (HarmonyOS PC aarch64).

Complete image processing suite supporting 200+ image formats.
Build system: autotools (configure + make).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ImagemagickFullConan(ConanFile):
    name = "imagemagick-full"
    version = "7.1.2-23"
    description = "Complete image processing suite supporting 200+ image formats"
    license = "Apache-2.0"
    homepage = "https://imagemagick.org"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libpng/1.6.58")
        self.requires("libtiff/4.7.2")
        self.requires("freetype/2.14.3")
        self.requires("fontconfig/2.18.1.1")
        self.requires("openjpeg/2.5.4")
        self.requires("libwebp/1.6.0")
        self.requires("libxml2/2.15.3.1")
        self.requires("lcms2/2.19")
        self.requires("xz/5.6.2")
        self.requires("bzip2/1.0.8")
        self.requires("zstd/1.5.7")
        # Pin zlib to match libtiff and libpng requirements (avoid 1.3.2 conflict)
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)

        tc.configure_args.extend([
            "--with-jpeg",
            "--with-png",
            "--with-tiff",
            "--with-freetype",
            "--with-fontconfig",
            "--with-openjp2",
            "--with-webp",
            "--with-xml",
            "--with-lcms",
            "--with-lzma",
            "--with-zlib",
            "--with-zstd",
            "--without-heic",
            "--without-djvu",
            "--without-openexr",
            "--without-raw",
            "--without-x",
            "--without-perl",
            "--disable-openmp",
        ])

        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])

        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        # On OHOS, add RPATH for shared library resolution.
        # LD_LIBRARY_PATH breaks the system lld linker (which depends on
        # libxml2.so.16), so we use -Wl,-rpath to embed RPATH in binaries.
        if str(self.settings.os) == "OHOS":
            lib_paths = []
            for dep in self.dependencies.values():
                for libdir in dep.cpp_info.libdirs:
                    lib_paths.append(libdir)
            if lib_paths:
                rpath = ":".join(lib_paths)
                tc.extra_ldflags.append(f"-Wl,-rpath,{rpath}")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: set umask 022 globally so configure's temp directories
        # are accessible (umask 077 creates 0700 dirs that current user
        # cannot write to on HMDFS where directory owner is inherited)
        os.umask(0o022)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = [
            "MagickCore-7.Q16HDRI",
            "MagickWand-7.Q16HDRI",
            "Magick++-7.Q16HDRI",
        ]
        self.cpp_info.includedirs = ["include/ImageMagick-7"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.defines = [
            "MAGICKCORE_QUANTUM_DEPTH=16",
            "MAGICKCORE_HDRI_ENABLE=1",
            "MAGICKCORE_CHANNEL_MASK_DEPTH=32",
        ]
        self.cpp_info.set_property("pkg_config_name", "MagickCore-7.Q16HDRI")
