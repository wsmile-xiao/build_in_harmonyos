#!/usr/bin/env python3
"""indi-gphoto — INDI driver for GPhoto2-supported DSLR/mirrorless cameras.

The driver lives in the indi-3rdparty monorepo (subdirectory indi-gphoto/,
v2.0.2 release tag, upstream driver version 3.2). Like indi-aok, the whole
repository tree is kept (source strip_root=True) because indi-gphoto's
CMakeLists.txt appends "../cmake_modules" to CMAKE_MODULE_PATH.

Adaptation points for OHOS (see notes.md):
  * All find_package() calls go through the monorepo's legacy Find*.cmake
    modules (variable-based: INDI_/CFITSIO_/GPHOTO2_/LibRaw_/USB1_/ZLIB/JPEG),
    so CMAKE_FIND_PACKAGE_PREFER_CONFIG is forced OFF (same pattern as the
    libindi 2.2.2.1 recipe) and every module is fed its hint variables from
    the Conan dependency package folders (R49: build-folder-local injection,
    never a shared system prefix).
  * INDI_DATA_DIR is preset to a relative path so indi_gphoto.xml installs
    into this package's own share/indi (not into libindi's package folder).
  * UDEVRULES_INSTALL_DIR is preset to a relative path (default is the
    absolute /usr/lib/udev/rules.d which is not writable on OHOS).
"""
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PreferConfigOffBlock(Block):
    """Force module mode so the monorepo's legacy Find*.cmake variables win."""
    template = textwrap.dedent("""\
        set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)
    """)


class IndigphotoConan(ConanFile):
    name = "indi-gphoto"
    version = "3.2-20221221172841"
    description = "INDI driver for GPhoto2-supported DSLR and mirrorless cameras"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty"
    url = "https://github.com/indilib/indi-3rdparty"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libindi/2.2.2.1")
        self.requires("libgphoto2/2.5.31")
        self.requires("cfitsio/4.6.4")
        self.requires("libraw/0.22.1")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libusb/1.0.27")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _first_lib(dep, names):
        """Return the absolute path of the first existing library file."""
        libdir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        for name in names:
            for ext in (".a", ".so"):
                candidate = os.path.join(libdir, "lib%s%s" % (name, ext))
                if os.path.exists(candidate):
                    return candidate
        raise ConanException("none of %s found in %s" % (names, libdir))

    def generate(self):
        tc = CMakeToolchain(self)

        # Legacy variable-based Find modules must not be shadowed by config
        # packages (same pattern as the libindi 2.2.2.1 recipe).
        tc.blocks["prefer_config_off"] = PreferConfigOffBlock

        # FindINDI.cmake: locate libindi inside its package folder (R49).
        indi = self.dependencies["libindi"]
        tc.variables["INDI_ROOT"] = indi.package_folder
        # Relative destination: install into this package, not libindi's.
        tc.variables["INDI_DATA_DIR"] = "share/indi"

        # FindCFITSIO.cmake (static-only archive).
        cfitsio = self.dependencies["cfitsio"]
        tc.variables["CFITSIO_INCLUDE_DIR"] = os.path.join(
            cfitsio.package_folder, cfitsio.cpp_info.includedirs[0])
        tc.variables["CFITSIO_LIBRARIES"] = self._first_lib(cfitsio, ["cfitsio"])

        # FindGPHOTO2.cmake.
        gphoto2 = self.dependencies["libgphoto2"]
        tc.variables["GPHOTO2_INCLUDE_DIR"] = os.path.join(
            gphoto2.package_folder, gphoto2.cpp_info.includedirs[0])
        tc.variables["GPHOTO2_LIBRARY"] = self._first_lib(gphoto2, ["gphoto2", "libgphoto2"])
        tc.variables["GPHOTO2_PORT_LIBRARY"] = self._first_lib(
            gphoto2, ["gphoto2_port", "libgphoto2_port"])

        # FindLibRaw.cmake (header lives under include/libraw/...).
        # Link by bare name with -L: the libraw package's shared object ships
        # without a SONAME, so passing the absolute .so path would bake the
        # Conan cache path into the driver's DT_NEEDED (E: absolute NEEDED).
        libraw = self.dependencies["libraw"]
        raw_libdir = os.path.join(libraw.package_folder, libraw.cpp_info.libdirs[0])
        tc.variables["LibRaw_INCLUDE_DIR"] = os.path.join(
            libraw.package_folder, libraw.cpp_info.includedirs[0])
        tc.variables["LibRaw_LIBRARIES"] = "raw"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-L%s -Wl,-rpath-link,%s" % (raw_libdir, raw_libdir)

        # FindUSB1.cmake (only include dirs are consumed by the driver).
        usb = self.dependencies["libusb"]
        tc.variables["USB1_INCLUDE_DIR"] = os.path.join(
            usb.package_folder, usb.cpp_info.includedirs[0])

        # Built-in FindZSSL/FindZLIB & FindJPEG.
        zlib = self.dependencies["zlib"]
        tc.variables["ZLIB_INCLUDE_DIR"] = os.path.join(
            zlib.package_folder, zlib.cpp_info.includedirs[0])
        tc.variables["ZLIB_LIBRARY"] = self._first_lib(zlib, ["z"])
        jpeg = self.dependencies["libjpeg-turbo"]
        tc.variables["JPEG_INCLUDE_DIR"] = os.path.join(
            jpeg.package_folder, jpeg.cpp_info.includedirs[0])
        tc.variables["JPEG_LIBRARY"] = self._first_lib(jpeg, ["jpeg", "jpeg-turbo", "turbojpeg"])

        # Default is the absolute /usr/lib/udev/rules.d (not writable on OHOS).
        tc.variables["UDEVRULES_INSTALL_DIR"] = "share/udev/rules.d"

        # v2.0.2-era CMakeCommon sets C++14; libindi 2.2.2 headers need C++17.
        tc.variables["CMAKE_CXX_STANDARD"] = "17"

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="indi-gphoto")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Only the driver executable, its symlink aliases and the INDI XML
        # descriptor are packaged.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        # The driver links against libindi's shared objects (libindidriver.so.2
        # and libindiclient.so.2), but libindi is published static-first
        # (shared=False), so Conan leaves its lib folder out of the run
        # environment. Declare the runtime search path here so the
        # test_package and downstream consumers can actually load the driver.
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                      self.dependencies["libindi"].cpp_info.libdirs[0])
