#!/usr/bin/env python3
"""Conan recipe for rdma-core 56.1 — CMake build (OHOS).

rdma-core provides userspace RDMA/InfiniBand libraries:
  - libibverbs (RDMA verbs API)
  - librdmacm (RDMA connection manager)
  - libibumad (InfiniBand MAD)
  - libibmad, libibnetdisc, infiniband-diags

Build strategy: Disable optional features not available on OHOS
(libnl, pyverbs, man pages, valgrind, symbol versioning).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class RdmaCoreConan(ConanFile):
    name = "rdma-core"
    version = "56.1"
    description = "RDMA core userspace libraries and daemons (libibverbs, librdmacm, libibumad)"
    license = "GPL-2.0 OR BSD-2-Clause"
    homepage = "https://github.com/linux-rdma/rdma-core"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "enable_resolve_neigh": [True, False],
        "enable_static": [True, False],
    }
    default_options = {
        "shared": False,
        "enable_resolve_neigh": False,
        "enable_static": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # rdma-core depends on:
        # - pthread (system, no conan package needed)
        # - libnl-3.0 (disabled via enable_resolve_neigh=False)
        # - libudev (optional, auto-detected)
        # - libsystemd (optional, auto-detected)
        # No conan dependencies required when all optional features are disabled
        pass

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rdma-core only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"],
            sha256=source_data.get("sha256", ""), strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS: disable optional features not available on platform
        tc.variables["ENABLE_RESOLVE_NEIGH"] = "ON" if self.options.enable_resolve_neigh else "OFF"
        tc.variables["NO_PYVERBS"] = "1"
        tc.variables["NO_MAN_PAGES"] = "1"
        tc.variables["ENABLE_STATIC"] = "ON" if self.options.enable_static else "OFF"
        tc.variables["NO_COMPAT_SYMS"] = "1"
        tc.variables["ENABLE_VALGRIND"] = "OFF"
        tc.variables["ENABLE_WERROR"] = "OFF"
        # OHOS E119 fix: prevent sys/socket.h from redefining sockaddr_storage
        # which conflicts with linux/socket.h. On OHOS (musl-based), __MUSL__
        # should be defined but isn't by the Clang compiler. Defining it makes
        # sys/socket.h skip its sockaddr_storage definition (guarded by #ifndef __MUSL__).
        tc.preprocessor_definitions["__MUSL__"] = "1"
        # Build shared or static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # CMake system name for cross-compilation
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Build core libraries: ibverbs, rdmacm, ibumad, ibmad, ibnetdisc, ccan, util
        # Try building all, fall back to specific targets if full build fails
        try:
            cmake.build()
        except Exception:
            self.output.warning("Full build failed, trying core libraries only...")
            cmake.build(target="ibverbs")
            cmake.build(target="rdmacm")
            cmake.build(target="ibumad")

    def package(self):
        cmake = CMake(self)
        # Try standard install first
        try:
            cmake.install()
        except Exception:
            self.output.warning("cmake.install() failed, manual packaging...")
            self._manual_package()

    def _manual_package(self):
        """Manually copy build artifacts if cmake.install() fails."""
        b = self.build_folder
        # Find build output
        out = None
        for candidate in (
            os.path.join(b, "build", "Release"),
            os.path.join(b, "Release"),
            b,
        ):
            if os.path.isdir(candidate):
                out = candidate
                break
        if out is None:
            out = b

        # Copy static libraries
        lib_dir = os.path.join(out, "lib")
        if os.path.isdir(lib_dir):
            pkg_lib = os.path.join(self.package_folder, "lib")
            os.makedirs(pkg_lib, exist_ok=True)
            for f in os.listdir(lib_dir):
                if f.endswith((".a", ".so")):
                    shutil.copy2(os.path.join(lib_dir, f),
                                 os.path.join(pkg_lib, f))

        # Copy headers
        src_root = os.path.join(os.path.dirname(os.path.dirname(self.build_folder)), "s")
        # kernel-headers
        for hdr_dir in [
            os.path.join(src_root, "kernel-headers", "include"),
            os.path.join(src_root, "libibverbs", "include"),
            os.path.join(src_root, "librdmacm", "include"),
            os.path.join(src_root, "libibumad", "include"),
            os.path.join(src_root, "libibmad", "include"),
        ]:
            if os.path.isdir(hdr_dir):
                self._copy_headers(hdr_dir)

        # Copy binaries
        bin_dir = os.path.join(out, "bin")
        if os.path.isdir(bin_dir):
            pkg_bin = os.path.join(self.package_folder, "bin")
            os.makedirs(pkg_bin, exist_ok=True)
            for f in os.listdir(bin_dir):
                if os.access(os.path.join(bin_dir, f), os.X_OK):
                    shutil.copy2(os.path.join(bin_dir, f),
                                 os.path.join(pkg_bin, f))

    def _copy_headers(self, src_dir):
        """Recursively copy headers preserving directory structure."""
        pkg_inc = os.path.join(self.package_folder, "include")
        for root, dirs, files in os.walk(src_dir):
            for f in files:
                if f.endswith((".h", ".hpp")):
                    rel = os.path.relpath(root, src_dir)
                    dst = os.path.join(pkg_inc, rel) if rel != "." else pkg_inc
                    os.makedirs(dst, exist_ok=True)
                    shutil.copy2(os.path.join(root, f), os.path.join(dst, f))

    def package_info(self):
        # rdma-core produces multiple libraries
        self.cpp_info.libs = [
            "ibverbs",
            "rdmacm",
            "ibumad",
            "ibmad",
            "ibnetdisc",
        ]
        self.cpp_info.system_libs = ["pthread", "rt", "dl"]
        self.cpp_info.set_property("cmake_file_name", "rdma-core")
        self.cpp_info.set_property("cmake_target_name", "rdma-core::rdma-core")
