#!/usr/bin/env python3
"""Conan recipe — airspyhf 1.6.8 (CMake project).

AirSpy HF+ user-mode driver (libairspyhf) and associated tools
(airspyhf_lib_version / airspyhf_info / airspyhf_rx / airspyhf_gpio /
airspyhf_calibrate) for Software Defined Radio.
Source: https://github.com/airspy/airspyhf (official tag 1.6.8)
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class AirspyhfConan(ConanFile):
    name = "airspyhf"
    version = "1.6.8"
    description = "AirSpy HF+ user-mode driver (libairspyhf) and associated tools"
    license = "BSD-3-Clause"
    homepage = "https://airspy.com/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
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

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # CMake 4.x compatibility: project declares cmake_minimum_required(2.8)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake does not recognize HarmonyOS, use Linux for compatibility
        # so that UNIX is set and the install(TARGETS ...) rules take effect.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CMAKE_BUILD_TYPE"] = "Release"

        # Upstream FindUSB1.cmake expects LIBUSB_INCLUDE_DIR / LIBUSB_LIBRARIES
        # (cache vars) rather than a conan-generated module. Resolve them from
        # the libusb/1.0.27 dependency package.
        libusb = self.dependencies["libusb"]
        usb_inc = os.path.join(libusb.package_folder, libusb.cpp_info.includedirs[0])
        tc.cache_variables["LIBUSB_INCLUDE_DIR"] = usb_inc
        if self.options.shared:
            usb_lib = os.path.join(libusb.package_folder, libusb.cpp_info.libdirs[0],
                                   "libusb-1.0.so")
        else:
            usb_lib = os.path.join(libusb.package_folder, libusb.cpp_info.libdirs[0],
                                   "libusb-1.0.a")
        tc.cache_variables["LIBUSB_LIBRARIES"] = usb_lib
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
        """HarmonyOS requires ELF code signing on shared libraries before
        they can be loaded by an executable, and on executables before they
        can run (SKILL §7; same as libusb and b2sum recipes)."""
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        targets = []
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for root, _, files in os.walk(libdir):
                for filename in files:
                    if ".so" in filename:
                        path = os.path.join(root, filename)
                        if not os.path.islink(path):
                            targets.append(path)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for filename in os.listdir(bindir):
                path = os.path.join(bindir, filename)
                if os.path.isfile(path) and not os.path.islink(path):
                    targets.append(path)
        for path in targets:
            subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
            signed = path + ".signed"
            r = subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed,
                                "-selfSign", "1", "-signAlg", "SHA256withECDSA"],
                               capture_output=True, text=True)
            if r.returncode == 0 and os.path.isfile(signed):
                os.replace(signed, path)
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["airspyhf"]
        self.cpp_info.libdirs = ["lib"]
        # Upstream installs headers to include/libairspyhf/ and tools use
        # #include <airspyhf.h> — expose that directory as the include path.
        self.cpp_info.includedirs = ["include/libairspyhf"]
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_module_file_name", "LIBAIRSPYHF")
        self.cpp_info.set_property("cmake_file_name", "airspyhf")
        self.cpp_info.set_property("pkg_config_name", "libairspyhf")
        # Runtime dependency: libusb (shared lib used by libairspyhf.so)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
