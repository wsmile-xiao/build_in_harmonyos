#!/usr/bin/env python3
"""Conan recipe for libftdi 0.20 - FTDI USB bridge driver library.

libftdi talks to FTDI USB-serial bridges (FT232/FT245 and friends) through the
libusb 0.1 API.  The package ships ``libftdi.so``/``libftdi.a`` and the public
``ftdi.h`` (which itself includes ``<usb.h>``, provided by the libusb-compat
layer).

The upstream tarball ships two build systems: autotools and CMake.  The CMake
path is used here because on OHOS the autotools path needs three separate
workarounds (see notes.md): configure hard-requires the ``libusb-config``
helper that the published libusb-compat package does not ship, libtool's echo
probe bakes the ksh-only ``print -r --`` into the generated libtool, and the
bundled ltmain.sh loses the escaping of ``old_archive_cmds`` under the
profile's CONFIG_SHELL.  Upstream's CMake instead finds libusb through
pkg-config / explicit cache variables and installs a pkg-config file whose
prefix CMakeToolchain already points at the package folder.

OHOS notes
----------
* ``FindUSB.cmake`` is bypassed with explicit cache variables resolved from the
  Conan dependency (``LIBUSB_INCLUDE_DIR`` / ``LIBUSB_LIBRARIES``), because the
  libusb/libusb-compat ``.pc`` files record release-worker prefixes.
* ``DOCUMENTATION=OFF`` (no doxygen), ``FTDIPP=OFF`` (the C++ wrapper needs
  boost) and ``PYTHON_BINDINGS=OFF``; examples stay enabled and
  ``examples/find_all`` is executed on the device as upstream evidence.
* ``ftdi.h`` publicly includes ``<usb.h>``, so libusb-compat is propagated with
  ``transitive_headers``/``transitive_libs``.
* ``package()`` drops ``bin/`` (the ``libftdi-config`` helper) and rewrites the
  dev paths of the installed ``libftdi.pc``.
"""
import glob
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibFtdiConan(ConanFile):
    name = "libftdi"
    version = "0.20"
    description = "FTDI USB bridge driver library (libusb 0.1 API)"
    license = "LGPL-2.0-or-later"
    homepage = "https://www.intra2net.com/en/developer/libftdi/"
    url = "https://www.intra2net.com/en/developer/libftdi/download.php"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # ftdi.h publicly includes <usb.h>, so the 0.1 compatibility layer
        # must reach consumers as well.
        self.requires("libusb-compat/0.1.7", transitive_headers=True, transitive_libs=True)

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libftdi is only supported on Linux/OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _absolute(library):
        folder = getattr(library, "package_folder", None) or ""
        return folder

    def generate(self):
        compat = self.dependencies["libusb-compat"]
        toolchain = CMakeToolchain(self)
        # FindUSB.cmake short circuits when both variables are set; resolving
        # them from the Conan dependency avoids the release-worker prefixes
        # recorded in the shipped .pc files.
        toolchain.cache_variables["LIBUSB_INCLUDE_DIR"] = os.path.join(
            self._absolute(compat), "include")
        libraries = [os.path.join(self._absolute(compat), "lib", "libusb.a")]
        libusb = self.dependencies.get("libusb")
        if libusb is not None and libusb.package_folder:
            for name in ("libusb-1.0.so", "libusb-1.0.a"):
                candidate = os.path.join(libusb.package_folder, "lib", name)
                if os.path.isfile(candidate):
                    libraries.append(candidate)
                    break
        toolchain.cache_variables["LIBUSB_LIBRARIES"] = ";".join(libraries)
        # The upstream project declares cmake_minimum_required(VERSION 2.6),
        # which CMake 4 refuses; allow the modern policy floor.
        toolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # CMake does not define UNIX for the unknown "HarmonyOS" system name,
        # but every install rule of this project is guarded by if(${UNIX}).
        toolchain.cache_variables["UNIX"] = "TRUE"
        toolchain.cache_variables["DOCUMENTATION"] = "OFF"
        toolchain.cache_variables["FTDIPP"] = "OFF"
        toolchain.cache_variables["PYTHON_BINDINGS"] = "OFF"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_program()

    def _run_upstream_program(self):
        if str(self.settings.os) != "OHOS" or platform.machine() not in ("aarch64", "arm64"):
            return
        candidates = glob.glob(os.path.join(self.build_folder, "**", "find_all"), recursive=True)
        candidates = [path for path in candidates if os.path.isfile(path)]
        if not candidates:
            return
        program = candidates[0]
        # The example links against the in-tree library with a *relative*
        # DT_NEEDED ("../src/libftdi.so"), so it has to run from its own
        # directory with the build's src/ and the libusb runtime in
        # LD_LIBRARY_PATH.
        library_paths = [os.path.join(self.build_folder, "src")]
        libusb = self.dependencies.get("libusb")
        if libusb is not None and libusb.package_folder:
            library_paths.append(os.path.join(libusb.package_folder, "lib"))
        log = os.path.join(self.build_folder, "upstream-find_all.log")
        # find_all enumerates FTDI devices; with no hardware attached it prints
        # "Number of FTDI devices found: 0" and exits 0.
        self.run('cd "{}" && LD_LIBRARY_PATH="{}" ./find_all > "{}" 2>&1'.format(
            os.path.dirname(program), os.pathsep.join(library_paths), log))
        self.output.info("upstream program OK: examples/find_all")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        shutil.rmtree(os.path.join(self.package_folder, "bin"), ignore_errors=True)
        # The upstream CMake installs libftdi.pc with CMAKE_INSTALL_PREFIX based
        # paths, but the generic "exec_prefix" points at .../bin; normalise it.
        # libftdipp.pc is installed unconditionally upstream even though the
        # C++ wrapper is disabled here.
        stray = os.path.join(self.package_folder, "lib", "pkgconfig", "libftdipp.pc")
        if os.path.isfile(stray):
            os.remove(stray)
        pkg_config = os.path.join(self.package_folder, "lib", "pkgconfig", "libftdi.pc")
        if os.path.isfile(pkg_config):
            with open(pkg_config, "r", encoding="utf-8") as handle:
                content = handle.read()
            content = content.replace("prefix=/", "prefix=" + self.package_folder)
            content = content.replace("exec_prefix=/", "exec_prefix=" + self.package_folder)
            content = content.replace("libdir=/lib",
                                      "libdir=" + os.path.join(self.package_folder, "lib"))
            content = content.replace("includedir=/include",
                                      "includedir=" + os.path.join(self.package_folder, "include"))
            with open(pkg_config, "w", encoding="utf-8") as handle:
                handle.write(content)
        copy(self, "COPYING.LIB", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["ftdi"]
        self.cpp_info.includedirs = ["include"]
        # ftdi.h includes <usb.h>; propagate the 0.1 compatibility layer.
        self.cpp_info.requires = ["libusb-compat::libusb-compat"]
        self.cpp_info.set_property("cmake_file_name", "libftdi")
        self.cpp_info.set_property("cmake_target_name", "libftdi::libftdi")
        self.cpp_info.set_property("pkg_config_name", "libftdi")
