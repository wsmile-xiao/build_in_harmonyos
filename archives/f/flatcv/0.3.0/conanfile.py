#!/usr/bin/env python3
"""Conan recipe for FlatCV - Pure C image processing library.

FlatCV uses a simple Makefile without autotools. We build manually.
"""
from conan import ConanFile
from conan.tools.files import get, copy, chdir, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class FlatcvConan(ConanFile):
    name = "flatcv"
    version = "0.3.0"
    description = "Image processing and computer vision library in pure C"
    license = "ISC"
    homepage = "https://flatcv.ad-si.com/"
    url = "https://github.com/ad-si/FlatCV"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"]["0.3.0"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        with chdir(self, self.source_folder):
            # Get compiler and flags
            cc = os.environ.get("CC", "clang")
            cflags = os.environ.get("CFLAGS", "-fPIC -O2")
            
            # Build library (exclude cli.c)
            lib_sources = [
                "src/binary_closing_disk.c",
                "src/conversion.c",
                "src/convert_to_binary.c",
                "src/corner_detection.c",
                "src/corner_peaks.c",
                "src/crop.c",
                "src/draw.c",
                "src/exif.c",
                "src/extract_document.c",
                "src/flip.c",
                "src/foerstner_corner.c",
                "src/histogram.c",
                "src/parse_hex_color.c",
                "src/perspectivetransform.c",
                "src/rgba_to_grayscale.c",
                "src/rotate.c",
                "src/single_to_multichannel.c",
                "src/sobel_edge_detection.c",
                "src/sort_corners.c",
                "src/trim.c",
                "src/watershed_segmentation.c",
            ]
            
            sources_str = " ".join(lib_sources)
            
            if self.options.shared:
                # Build shared library
                self.run(f"{cc} {cflags} -Wall -Wextra -Wpedantic -shared "
                        f"-Iinclude {sources_str} -lm -o libflatcv.so")
            else:
                # Build static library
                self.run(f"{cc} {cflags} -Wall -Wextra -Wpedantic -c "
                        f"-Iinclude {sources_str}")
                self.run("llvm-ar rcs libflatcv.a *.o")
            
            # Generate amalgamated header
            self.run("make flatcv.h")
            
            # Build CLI tool
            all_sources = sources_str + " src/cli.c"
            self.run(f"{cc} {cflags} -Wall -Wextra -Wpedantic "
                    f"-Iinclude {all_sources} -lm -o flatcv")

    def package(self):
        copy(self, "license.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "flatcv.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        
        if self.options.shared:
            copy(self, "libflatcv.so", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        else:
            copy(self, "libflatcv.a", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        
        # Package CLI tool
        copy(self, "flatcv", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["flatcv"]
        self.cpp_info.system_libs = ["m"]
        
        # Set bindir for CLI tool
        self.cpp_info.bindirs = ["bin"]
