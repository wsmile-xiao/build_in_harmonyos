#!/usr/bin/env python3
"""Conan recipe — apitrace 14.0 (CMake).

apitrace: API call tracing framework for OpenGL, Direct3D and other graphics APIs.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class ApitraceConan(ConanFile):
    name = "apitrace"
    version = "14.0"
    description = "API call tracing framework for OpenGL, Direct3D and other graphics APIs"
    license = "MIT"
    homepage = "https://github.com/apitrace/apitrace"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Download main source
        get(self, **self.conan_data["sources"], strip_root=True)

        # Download each submodule and extract into the correct path
        for sub in self.conan_data.get("submodules", []):
            dest = os.path.join(self.source_folder, sub["path"])
            os.makedirs(dest, exist_ok=True)
            get(self, url=sub["url"], sha256=sub["sha256"],
                destination=dest, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS is not recognised by CMake; build as Linux (native OHOS clang)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # Disable optional features that require unavailable platform libraries
        tc.variables["ENABLE_GUI"] = "OFF"
        tc.variables["ENABLE_X11"] = "OFF"
        tc.variables["ENABLE_EGL"] = "OFF"
        tc.variables["ENABLE_WAFFLE"] = "OFF"
        tc.variables["ENABLE_CLI"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["ENABLE_TESTS"] = "OFF"
        # Use GNU ld instead of lld; lld in OHOS SDK depends on libxml2.so.16
        # which may be missing on some CI workers
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-fuse-ld=ld"
        tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = "-fuse-ld=ld"
        tc.cache_variables["CMAKE_MODULE_LINKER_FLAGS"] = "-fuse-ld=ld"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Workaround: lld (OHOS SDK linker) depends on libxml2.so.16 but
        # the system has libxml2.so.2 (version 2.11.9). Create symlink in
        # a writable temp dir and add to LD_LIBRARY_PATH.
        import os, tempfile
        libxml2_so2 = "/data/service/hnp/libxml2.org/libxml2_2.11.9/lib/libxml2.so.2"
        if os.path.exists(libxml2_so2) and not os.path.exists("/data/service/hnp/libxml2.org/libxml2_2.11.9/lib/libxml2.so.16"):
            tmpdir = tempfile.mkdtemp(prefix="libxml2-fix-")
            so16 = os.path.join(tmpdir, "libxml2.so.16")
            os.symlink(libxml2_so2, so16)
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = tmpdir + (":" + existing if existing else "")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
