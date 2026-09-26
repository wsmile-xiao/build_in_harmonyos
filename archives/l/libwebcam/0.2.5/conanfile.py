#!/usr/bin/env python3
"""Conan recipe — libwebcam 0.2.5 (CMake).

libwebcam: a userspace library for handling UVC webcam controls via V4L2,
part of the Linux UVC project. Also builds the uvcdynctrl command-line tool.
Source: Debian pool (pristine upstream .orig.tar.gz), homepage SourceForge.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm, rmdir, apply_conandata_patches, export_conandata_patches


class LibwebcamConan(ConanFile):
    name = "libwebcam"
    version = "0.2.5"
    description = "Webcam control library for UVC devices (V4L2 extensions)"
    license = "LGPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/libwebcam/"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # libwebcam uses libxml2 for parsing UVC control mapping XML files.
        self.requires("libxml2/2.15.3.1")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream cmake_minimum_required(VERSION 2.6); CMake 4.x needs a
        # policy floor to parse project() calls.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # uvcdynctrl binary needs to find libwebcam.so in ../lib at runtime.
        tc.cache_variables["CMAKE_INSTALL_RPATH"] = r"\$ORIGIN/../lib"

        # Inject libxml2 location (bypasses pkg-config, which is unreliable on
        # the headless OHOS builder). The patched CMakeLists reads these
        # variables instead of calling pkg_check_modules().
        libxml2 = self.dependencies["libxml2"]
        xml_inc = os.path.join(libxml2.package_folder, libxml2.cpp_info.includedirs[0])
        tc.cache_variables["LIBXML2_INCLUDE_DIRS"] = xml_inc
        xml_lib_name = "libxml2.so" if libxml2.options.shared else "libxml2.a"
        xml_lib = os.path.join(libxml2.package_folder, libxml2.cpp_info.libdirs[0], xml_lib_name)
        tc.cache_variables["LIBXML2_LIBRARIES"] = xml_lib

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._emit_upstream_test_audit()

    def _emit_upstream_test_audit(self):
        """Upstream test audit (R51).

        libwebcam 0.2.5 has no automated test framework:
        - CMakeLists.txt: no enable_testing()/add_test()/ctest.
        - libwebcam/test.c is a hardware integration demo that opens /dev/video0
          and enumerates physical camera controls; it is NOT registered as a
          CTest/make check target. Running it requires a physical UVC camera.
        - uvcdynctrl is a CLI tool, not a test.

        Discovered: 0 automated test cases (gtest/make-check/ctest).
        The headless OHOS builder has no camera, so test.c cannot run here.
        """
        import json
        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "audit: no ctest/gtest/make-check; libwebcam/test.c requires physical UVC camera",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "Audited libwebcam 0.2.5: root CMakeLists.txt and subdirectory "
                "CMakeLists.txt have no enable_testing/add_test/ctest, no gtest, "
                "no 'make check' target. libwebcam/test.c opens /dev/video0 and "
                "enumerates physical camera controls; it is not registered as a "
                "build target and requires a physical UVC camera. Counted 0 "
                "automated test-framework cases."
            ),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Remove the pkg-config .pc file (Conan manages dependency info).
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        if os.path.isdir(pc_dir):
            rm(self, "*.pc", pc_dir)
        # Remove udev rules and scripts — not applicable on OHOS.
        udev_dir = os.path.join(self.package_folder, "lib", "udev")
        if os.path.isdir(udev_dir):
            rmdir(self, udev_dir)
        # Install license.
        copy(self, "COPYING.LESSER",
             os.path.join(self.source_folder, "libwebcam"),
             os.path.join(self.package_folder, "licenses"))
        self._sign_elf()

    def _sign_elf(self):
        """HarmonyOS requires ELF code signing (same as libuvc/libusb)."""
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        for sub in ("lib", "bin"):
            d = os.path.join(self.package_folder, sub)
            if not os.path.isdir(d):
                continue
            for root, _, files in os.walk(d):
                for filename in files:
                    path = os.path.join(root, filename)
                    if not filename.endswith((".so", "")) and sub == "lib":
                        continue
                    if sub == "bin" and not os.access(path, os.X_OK):
                        continue
                    if sub == "lib" and ".so" not in filename and not filename.endswith(".a"):
                        continue
                    if os.path.islink(path):
                        continue
                    if path.endswith(".a"):
                        continue
                    subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
                    signed = path + ".signed"
                    result = subprocess.run(
                        [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
                        capture_output=True, text=True,
                    )
                    if result.returncode == 0 and os.path.isfile(signed):
                        os.replace(signed, path)
                        os.chmod(path, 0o755)

    def package_info(self):
        # The library target outputs libwebcam.so / libwebcam.a (OUTPUT_NAME "webcam").
        self.cpp_info.libs = ["webcam"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libwebcam")
        self.cpp_info.set_property("cmake_target_name", "libwebcam::webcam")
        self.cpp_info.set_property("pkg_config_name", "libwebcam")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
