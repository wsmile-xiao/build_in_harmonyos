#!/usr/bin/env python3
"""Conan recipe for librevenge 0.0.5 — Base library for document format conversion.

librevenge provides RVNGString, RVNGStringVector, RVNGPropertyList, RVNGBinaryData,
and other primitives used by document format converters (libvisio, libwpd, etc.).

Build system: Autotools (configure + make)
License: LGPL-2.1-or-later OR MPL-2.0
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class LibrevengeConan(ConanFile):
    name = "librevenge"
    version = "0.0.5"
    description = "Base library for document format conversion (REVENGE project)"
    license = "LGPL-2.1-or-later OR MPL-2.0"
    homepage = "https://sourceforge.net/p/librevenge/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # librevenge uses boost headers (header-only, no linking needed).
        # RVNGBinaryData.cpp uses boost/archive/iterators/base64_from_binary.hpp
        # (Boost.Serialization module). The boost/1.91.0 package in the repo
        # is a Redex-tailored slim build that omits serialization; boost/1.90.0.3
        # is the latest published package that ships serialization headers.
        self.requires("boost/1.90.0.3")
        # librevenge-stream uses zlib for decompression
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # E001/E096: cross-compile triplet for HarmonyOS (build machine cannot
        # run OHOS binaries, so configure must skip the "cannot run C compiled
        # programs" check via --host; autotools then treats us as cross build).
        if self.settings.os == "OHOS":
            tc.configure_args.append("--host=aarch64-linux-ohos")
            tc.configure_args.append("--build=aarch64-linux")
        tc.generate()
        # Generate dependency flags (boost include paths etc.)
        deps = AutotoolsDeps(self)
        deps.generate()
        # Skip cppunit check (test-only dependency, not needed for building)
        env = Environment()
        env.define("CPPUNIT_CFLAGS", " ")
        env.define("CPPUNIT_LIBS", " ")
        # Set zlib paths for pkg-config based configure check
        zlib = self.dependencies["zlib"]
        zlib_root = zlib.package_folder
        env.define("ZLIB_CFLAGS", f"-I{zlib_root}/include")
        env.define("ZLIB_LIBS", f"-L{zlib_root}/lib -lz")
        envvars = env.vars(self)
        envvars.save_script("conanbuildenv_skip_cppunit")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CMake properties for find_package() / target_link_libraries()
        self.cpp_info.set_property("cmake_file_name", "librevenge")
        self.cpp_info.set_property("cmake_target_name", "librevenge::librevenge")

        # librevenge produces 3 libraries with versioned names (libtool convention)
        # Include path: include/librevenge-0.0/
        # Library files: librevenge-0.0.a, librevenge-generators-0.0.a, librevenge-stream-0.0.a
        self.cpp_info.libs = ["revenge-0.0", "revenge-generators-0.0", "revenge-stream-0.0"]
        self.cpp_info.includedirs = ["include/librevenge-0.0"]
