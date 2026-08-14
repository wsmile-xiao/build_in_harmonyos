#!/usr/bin/env python3
"""Conan recipe — ImageMagick 7.1.2.29

ImageMagick is a free, open-source software suite for creating,
editing, converting, and displaying images.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ImageMagickConan(ConanFile):
    name = "imagemagick"
    version = "7.1.2.29"
    description = "Open-source software suite for creating, editing, converting, and displaying images"
    license = "ImageMagick"
    homepage = "https://imagemagick.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_magick_plus_plus": [True, False],
    }
    default_options = {
        "shared": False,
        "with_magick_plus_plus": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libpng/1.6.58")
        self.requires("libtiff/4.7.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: static linking for system-name libraries
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        # Disable OpenMP (not well supported on OHOS)
        tc.configure_args.append("--disable-openmp")
        # Disable delegates not available in OHOS conan repo
        tc.configure_args.append("--without-heic")
        tc.configure_args.append("--without-openjp2")
        tc.configure_args.append("--without-openexr")
        tc.configure_args.append("--without-raw")
        tc.configure_args.append("--without-djvu")
        tc.configure_args.append("--without-jxl")
        tc.configure_args.append("--without-lqr")
        tc.configure_args.append("--without-pango")
        tc.configure_args.append("--without-lcms")
        tc.configure_args.append("--without-zstd")
        tc.configure_args.append("--without-jbig")
        tc.configure_args.append("--without-raqm")
        tc.configure_args.append("--without-gdi32")
        tc.configure_args.append("--without-bzlib")
        tc.configure_args.append("--without-zip")
        tc.configure_args.append("--without-dmr")
        if not self.options.with_magick_plus_plus:
            tc.configure_args.append("--without-magick-plus-plus")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # ImageMagick installs headers under include/ImageMagick-7/
        imagemagick_include = "include/ImageMagick-7"
        # Required compile definitions for all ImageMagick consumers
        magick_defines = [
            "MAGICKCORE_QUANTUM_DEPTH=16",
            "MAGICKCORE_HDRI_ENABLE=1",
            "MAGICKCORE_CHANNEL_MASK_DEPTH=32",
        ]
        # MagickCore is the core library
        self.cpp_info.components["MagickCore"].libs = ["MagickCore-7.Q16HDRI"]
        self.cpp_info.components["MagickCore"].includedirs = [imagemagick_include]
        self.cpp_info.components["MagickCore"].defines = magick_defines
        self.cpp_info.components["MagickCore"].requires = ["zlib::zlib", "libjpeg-turbo::libjpeg-turbo", "libpng::libpng", "libtiff::libtiff"]
        self.cpp_info.components["MagickCore"].set_property("cmake_target_name", "ImageMagick::MagickCore")
        # MagickWand depends on MagickCore
        self.cpp_info.components["MagickWand"].libs = ["MagickWand-7.Q16HDRI"]
        self.cpp_info.components["MagickWand"].includedirs = [imagemagick_include]
        self.cpp_info.components["MagickWand"].defines = magick_defines
        self.cpp_info.components["MagickWand"].requires = ["MagickCore"]
        self.cpp_info.components["MagickWand"].set_property("cmake_target_name", "ImageMagick::MagickWand")
        # Magick++ (C++ bindings) depends on MagickWand
        if self.options.with_magick_plus_plus:
            self.cpp_info.components["Magick++"].libs = ["Magick++-7.Q16HDRI"]
            self.cpp_info.components["Magick++"].includedirs = [imagemagick_include]
            self.cpp_info.components["Magick++"].defines = magick_defines
            self.cpp_info.components["Magick++"].requires = ["MagickWand"]
            self.cpp_info.components["Magick++"].set_property("cmake_target_name", "ImageMagick::Magick++")
        self.cpp_info.set_property("cmake_file_name", "ImageMagick")
