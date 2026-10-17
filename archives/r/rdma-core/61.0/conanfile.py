#!/usr/bin/env python3
"""Conan recipe for rdma-core 61.0 — CMake build (OHOS).

rdma-core provides userspace RDMA/InfiniBand libraries:
  - libibverbs (RDMA verbs API)
  - librdmacm (RDMA connection manager)
  - libibumad (InfiniBand MAD)
  - libibmad, libibnetdisc, infiniband-diags tools

Build strategy (inherited from 56.1 adaptation, revalidated for 61.0):
disable optional features not available on OHOS (libnl, pyverbs, man pages,
valgrind, GNU symbol versioning), plus portability fixes for OHOS musl libc:
  - sockaddr_storage redefinition (netlink-attr.h forward decl)
  - rindex -> strrchr (srp_daemon)
  - program_invocation_short_name -> __progname (preload.c)
  - getpass weak implementation (infiniband-diags)
  - pthread_cancel unavailable -> signal-based thread exit (rping example)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class RdmaCoreConan(ConanFile):
    name = "rdma-core"
    version = "61.0"
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
        # rdma-core depends on pthread/rt/dl (system libs) only when the
        # optional features (libnl, pyverbs, man pages, valgrind) are off.
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
        # Conan toolchain defaults CMAKE_INSTALL_LIBEXECDIR to "bin", which
        # collides with the srp_daemon executable at bin/srp_daemon when
        # cmake installs start_on_all_ports into ${LIBEXECDIR}/srp_daemon.
        tc.variables["CMAKE_INSTALL_LIBEXECDIR"] = "libexec"
        tc.generate()

    def build(self):
        # Patches are already applied in source() -- do not re-apply here.
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

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
