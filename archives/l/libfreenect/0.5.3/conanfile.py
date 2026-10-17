#!/usr/bin/env python3
"""Conan recipe — libfreenect 0.5.3 (CMake project).

OpenKinect user-space driver for the Microsoft Kinect. Builds the core
``freenect`` library and the ``freenect_sync`` synchronous wrapper.
Source: https://github.com/OpenKinect/libfreenect (official tag v0.5.3)
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    replace_in_file,
)
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class LibfreenectConan(ConanFile):
    name = "libfreenect"
    version = "0.5.3"
    description = "OpenKinect driver for the Microsoft Kinect (libfreenect)"
    license = "Apache-2.0 OR GPL-2.0"
    homepage = "https://openkinect.org/"
    url = "https://github.com/OpenKinect/libfreenect"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._patch_sources()

    def _patch_sources(self):
        # HMDFS cannot create symlinks. Upstream sets VERSION/SOVERSION on the
        # shared libraries, which makes CMake emit libfreenect.so.0.5.3 ->
        # libfreenect.so.0.5 -> libfreenect.so symlinks and fail with
        # "Permission denied". Drop the versioning so CMake installs a flat
        # libfreenect.so / libfreenect_sync.so.
        src_cmake = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        replace_in_file(
            self,
            src_cmake,
            "set_target_properties ( freenect PROPERTIES\n"
            "  VERSION ${PROJECT_VER}\n"
            "  SOVERSION ${PROJECT_APIVER})",
            "# versioning dropped: HMDFS has no symlinks (flat .so)",
        )
        sync_cmake = os.path.join(
            self.source_folder, "wrappers", "c_sync", "CMakeLists.txt"
        )
        replace_in_file(
            self,
            sync_cmake,
            "set_target_properties (freenect_sync PROPERTIES\n"
            "  VERSION ${PROJECT_VER}\n"
            "  SOVERSION ${PROJECT_APIVER})",
            "# versioning dropped: HMDFS has no symlinks (flat .so)",
        )

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # CMake 4.x compatibility: upstream declares cmake_minimum_required(2.6)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake does not recognize HarmonyOS; report Linux so UNIX is set
        # and the install(TARGETS ...) rules take effect.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CMAKE_BUILD_TYPE"] = "Release"
        # aarch64 is little-endian. Pre-set BIG_ENDIAN so test_big_endian()
        # does not emit a cross-compilation try_run (which cannot run here).
        tc.cache_variables["BIG_ENDIAN"] = "FALSE"

        # Disable optional components that need GLUT/OpenGL, python or a
        # display. Keep the core C library and the thin c_sync wrapper.
        tc.cache_variables["BUILD_EXAMPLES"] = "OFF"
        tc.cache_variables["BUILD_FAKENECT"] = "OFF"
        tc.cache_variables["BUILD_C_SYNC"] = "ON"
        tc.cache_variables["BUILD_CPP"] = "ON"
        # ON = install fwfetcher.py only, do NOT run python to embed firmware.
        tc.cache_variables["BUILD_REDIST_PACKAGE"] = "ON"

        # Upstream cmake_modules/Findlibusb-1.0.cmake runs find_path/find_library
        # against hardcoded /usr/include,/usr/lib and early-returns when the
        # plural cache vars are already set. Resolve them from the conan
        # libusb/1.0.27 dependency so cross-compilation finds it.
        libusb = self.dependencies["libusb"]
        usb_inc = os.path.join(libusb.package_folder, libusb.cpp_info.includedirs[0])
        if self.options.shared:
            usb_lib = os.path.join(
                libusb.package_folder, libusb.cpp_info.libdirs[0], "libusb-1.0.so"
            )
        else:
            usb_lib = os.path.join(
                libusb.package_folder, libusb.cpp_info.libdirs[0], "libusb-1.0.a"
            )
        tc.cache_variables["LIBUSB_1_INCLUDE_DIRS"] = usb_inc
        tc.cache_variables["LIBUSB_1_LIBRARIES"] = usb_lib
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_elf()

    def _sign_elf(self):
        """HarmonyOS requires ELF code signing on shared libraries before they
        can be loaded (SKILL §7; same as libusb and airspyhf recipes)."""
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _, files in os.walk(libdir):
            for filename in files:
                if ".so" not in filename:
                    continue
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    continue
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", path], check=False
                )
                signed = path + ".signed"
                r = subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", signed,
                     "-selfSign", "1", "-signAlg", "SHA256withECDSA"],
                    capture_output=True, text=True,
                )
                if r.returncode == 0 and os.path.isfile(signed):
                    os.replace(signed, path)
                    os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["freenect", "freenect_sync"]
        self.cpp_info.libdirs = ["lib"]
        # Upstream installs public headers into include/libfreenect/.
        self.cpp_info.includedirs = ["include/libfreenect"]
        self.cpp_info.set_property("cmake_file_name", "libfreenect")
        self.cpp_info.set_property("cmake_target_name", "libfreenect::libfreenect")
        self.cpp_info.set_property("pkg_config_name", "libfreenect")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m"]
