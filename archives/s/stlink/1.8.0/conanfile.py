#!/usr/bin/env python3
"""Conan recipe — stlink 1.8.0 (CMake project).

stlink is a toolset and library for flashing and debugging STM32 MCUs via
ST-LINK USB adapters:
- libstlink (shared/static library, OUTPUT_NAME stlink)
- command-line tools: st-flash, st-info, st-util, st-trace
Source: https://github.com/stlink-org/stlink (official tag v1.8.0)
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class StlinkConan(ConanFile):
    name = "stlink"
    version = "1.8.0"
    description = "STM32 ST-LINK toolset and library (st-flash / st-info / st-util / st-trace)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/stlink-org/stlink"
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
        # stlink determines the version via `git describe`; in source-tarball
        # mode (no .git) get_version.cmake falls back to a local .version
        # file and errors out if it is missing — provide it from the recipe.
        version_file = os.path.join(self.source_folder, ".version")
        if not os.path.exists(version_file):
            with open(version_file, "w", encoding="utf-8") as fh:
                fh.write(self.version)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # E092: CMake does not recognize HarmonyOS, use Linux for compatibility
        # so that UNIX rules and install(TARGETS ...) take effect.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CMAKE_BUILD_TYPE"] = "Release"

        # Upstream Findlibusb.cmake expects LIBUSB_INCLUDE_DIR / LIBUSB_LIBRARY
        # (cache vars) rather than a conan-generated module. Resolve them from
        # the libusb/1.0.27 dependency package.
        libusb = self.dependencies["libusb"]
        usb_inc_base = os.path.join(libusb.package_folder, libusb.cpp_info.includedirs[0])
        candidate = os.path.join(usb_inc_base, "libusb-1.0")
        usb_inc = candidate if os.path.isdir(candidate) else usb_inc_base
        tc.cache_variables["LIBUSB_INCLUDE_DIR"] = usb_inc
        if self.options.shared:
            usb_lib = os.path.join(libusb.package_folder, libusb.cpp_info.libdirs[0],
                                   "libusb-1.0.so")
        else:
            usb_lib = os.path.join(libusb.package_folder, libusb.cpp_info.libdirs[0],
                                   "libusb-1.0.a")
        tc.cache_variables["LIBUSB_LIBRARY"] = usb_lib

        # udev/modprobe config defaults to absolute host paths (/etc, /lib);
        # redirect into the package so install stays self-contained.
        tc.cache_variables["STLINK_MODPROBED_DIR"] = "etc/modprobe.d"
        tc.cache_variables["STLINK_UDEV_RULES_DIR"] = "etc/udev/rules.d"
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
        can run (SKILL §7; same as libusb and airspyhf recipes)."""
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
        self.cpp_info.libs = ["stlink"]
        # Upstream installs headers to include/stlink/ (STLINK_INCLUDE_PATH).
        self.cpp_info.includedirs = ["include/stlink"]
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "stlink")
        self.cpp_info.set_property("pkg_config_name", "libstlink")
        # Runtime dependency: libusb (shared lib used by libstlink.so)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
