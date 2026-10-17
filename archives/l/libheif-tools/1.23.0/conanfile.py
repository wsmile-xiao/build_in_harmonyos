#!/usr/bin/env python3
"""Conan recipe - libheif-tools 1.23.0 (HEIF/AVIF container CLI).

Upstream: https://github.com/strukturag/libheif (tag v1.23.0)

This package ships the upstream command line tools only:

    heif-info   - dump the container structure / image properties
    heif-dec    - extract an image (installed upstream as heif-dec)
    heif-convert- the historical name of heif-dec, installed as a symlink
    heif-enc    - package an image into a HEIF/AVIF container

The library itself belongs to the separate `libheif` package, so this recipe
links it statically and then trims the install tree down to bin/ + man pages;
libheif.a, the public headers, the pkg-config file and the CMake package
config never appear in two packages at once.

Upstream has no `tools` option.  The command line tools live in
`examples/CMakeLists.txt`, and that directory is only entered from
`if(WITH_EXAMPLES)`.  WITH_EXAMPLES therefore doubles as "build the tools",
and it also has to be told apart from the two *other* things it gates:
WITH_EXAMPLE_HEIF_VIEW (needs SDL2) and WITH_EXAMPLE_HEIF_THUMB (needs
libpng, and installs the heif-thumbnailer Nautilus plugin rather than a
command line tool).  heifio, the static helper library behind heif-dec /
heif-enc, additionally probes the build machine for JPEG / PNG / WebP /
TIFF input formats through find_package(); those probes are switched off
here so the package stays hermetic and never links the device's own
/usr/local copies by accident.  The WebP probe also has to be disabled
under upstream's own spelling - find_package(WEBP), all caps - because
CMAKE_DISABLE_FIND_PACKAGE_<name> matches the argument case-sensitively.

One source-level portability fix travels as a patch.  libheif/box.cc calls the
C++20 ranges algorithms std::ranges::all_of / std::ranges::find, and the libc++
that ships with the OHOS SDK (clang 15.0.4) declares the std::ranges namespace
but implements none of the ranges algorithms - the file fails to compile at
every -std= level, including the C++20 that upstream asks for.  Patch 0001
rewrites the three call sites as their <algorithm> equivalents.

Codecs stay off, exactly like the libheif archive: this is a container-only,
codec-free build.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)

# heifio finds these through CMake's Find modules; disabling the probes keeps
# the build hermetic (no accidental host linkage) and the package small.
# The names must match the argument upstream passes to find_package() exactly:
# CMAKE_DISABLE_FIND_PACKAGE_<name> is case-sensitive, and heifio spells the
# WebP probe find_package(WEBP).  "WebP" therefore disabled nothing and the
# device's /usr/local WEBPConfig.cmake was found instead, which aborts the
# configure step with an imported target pointing at a libsharpyuv.so.0.1.2
# that the system install never shipped.
HEIFIO_FORMAT_PROBES = ("JPEG", "PNG", "WEBP", "TIFF")

CODEC_OPTIONS = (
    "WITH_LIBDE265",
    "WITH_X265",
    "WITH_KVAZAAR",
    "WITH_UVG266",
    "WITH_VVDEC",
    "WITH_VVENC",
    "WITH_X264",
    "WITH_OpenH264_DECODER",
    "WITH_DAV1D",
    "WITH_AOM_DECODER",
    "WITH_AOM_ENCODER",
    "WITH_SvtEnc",
    "WITH_RAV1E",
    "WITH_JPEG_DECODER",
    "WITH_JPEG_ENCODER",
    "WITH_OpenJPEG_ENCODER",
    "WITH_OpenJPEG_DECODER",
    "WITH_OPENJPH_ENCODER",
    "WITH_FFMPEG_DECODER",
)


class LibheifToolsConan(ConanFile):
    name = "libheif-tools"
    version = "1.23.0"
    description = ("Command line tools for libheif - inspect and repack "
                   "HEIF/AVIF containers")
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/strukturag/libheif"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libheif-tools supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Static libheif + static heifio: the tools then need nothing but libc
        # at runtime and this package never ships a .so that could collide
        # with the libheif package.
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # The only switch that reaches examples/CLI tools at all.
        tc.variables["WITH_EXAMPLES"] = "ON"
        # Two extra things the same switch would otherwise drag in.
        tc.variables["WITH_EXAMPLE_HEIF_VIEW"] = "OFF"    # needs SDL2
        tc.variables["WITH_EXAMPLE_HEIF_THUMB"] = "OFF"   # needs libpng, plugin not CLI
        tc.variables["BUILD_DEVELOPMENT_TOOLS"] = "OFF"   # heif-gen-bayer etc.
        tc.variables["WITH_GDK_PIXBUF"] = "OFF"
        tc.variables["ENABLE_PLUGIN_LOADING"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["WITH_FUZZERS"] = "OFF"
        tc.variables["WITH_UNCOMPRESSED_CODEC"] = "OFF"
        # Opt-out upstream (defaults to ON) and it probes the same /usr/local
        # libwebp family as heifio's WebP probe.  With every codec off there is
        # no colour space conversion left to accelerate, so skip the probe.
        tc.variables["WITH_LIBSHARPYUV"] = "OFF"
        for opt in CODEC_OPTIONS:
            tc.variables[opt] = "OFF"
        for pkg in HEIFIO_FORMAT_PROBES:
            tc.variables[f"CMAKE_DISABLE_FIND_PACKAGE_{pkg}"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # Library-side install tree: cmake.install() also emits libheif.a,
        # the public headers, libheif.pc and lib/cmake/libheif.  Those belong
        # to the libheif package - drop them so the two can never collide.
        # share/man/man1 is kept: the man pages describe the tools shipped here.
        for name in ("include", "lib"):
            path = os.path.join(self.package_folder, name)
            if os.path.isdir(path):
                rmdir(self, path)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS only loads ELF binaries that carry a valid .codesign
        # section; llvm-objcopy/binary-sign-tool ship in the OHOS SDK.
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            # heif-convert is a symlink to heif-dec and is signed through it.
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            if not self._is_elf(path):
                continue
            self.run(
                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                    oc=objcopy, f=path
                )
            )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=path
                )
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = []
        self.cpp_info.libs = []