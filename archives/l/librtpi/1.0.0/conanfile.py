#!/usr/bin/env python3
"""Conan recipe for librtpi 1.0.0 — Real-Time Priority Inheritance library.

Upstream builds with autotools, but the 1.0.0 release tarball ships only
configure.ac (no generated configure), and `autoreconf --install` cannot run
on the OHOS PC image: autoconf/automake/libtoolize/m4 are absent (probed
2026-09-18 in $HOME/usr/local/bin and /data/service/hnp/bin; clang/cmake/
ninja/make are present, and the CI matrix lists cmake as available).  The
recipe therefore wraps the two upstream C translation units in a minimal
CMakeLists.txt (shipped via export_sources; upstream sources are not
modified) and builds with CMakeToolchain, reproducing the upstream install
layout:

  lib/librtpi.a | lib/librtpi.so(.1)
  include/rtpi.h  include/rtpi_internal.h
  include/rtpi/condition_variable.hpp  include/rtpi/mutex.hpp

OHOS specifics:
  - OHOS musl libc has no pthread cancellation family (E127):
    pthread_setcancelstate / pthread_setcanceltype / pthread_cancel are
    absent from libc.so (verified with `llvm-nm -D libc.so`).  librtpi's
    ENABLE_CANCELLATION code path uses exactly those calls, so the recipe
    forces the upstream --disable-cancellation configuration on OHOS
    (the upstream glibc-tests suite ships a dedicated branch for this build).
  - librtpi implements priority inheritance through the Linux PI futex
    syscalls (FUTEX_LOCK_PI / FUTEX_UNLOCK_PI / FUTEX_WAIT_REQUEUE_PI /
    FUTEX_CMP_REQUEUE_PI).  Compiling only needs <linux/futex.h>, which is
    present in the OHOS sysroot; whether the target kernel implements the
    PI futex ops is a runtime property that the test_package probes.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

required_conan_version = ">=2.0"


class LibrtpiConan(ConanFile):
    name = "librtpi"
    version = "1.0.0"
    description = (
        "Real-Time Priority Inheritance library for pthread mutexes and "
        "condition variables (Linux PI futex based)"
    )
    license = "LGPL-2.1-only"
    homepage = "https://gitlab.com/linux-rt/librtpi"
    url = "https://gitlab.com/linux-rt/librtpi"
    topics = ("real-time", "pthread", "priority-inheritance", "futex")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "cancellation": [True, False],
    }
    default_options = {
        "shared": False,
        "cancellation": True,
    }

    def export_sources(self):
        export_conandata_patches(self)
        # CMake wrapper for the autotools-only upstream tarball; see module
        # docstring for why autoreconf is not viable on OHOS.
        copy(self, "CMakeLists.txt",
             src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "librtpi implements Linux PI futex semantics (FUTEX_LOCK_PI "
                "family) and only targets Linux-family platforms"
            )

    def generate(self):
        cancellation = bool(self.options.cancellation)
        if self.settings.os == "OHOS" and cancellation:
            # E127: OHOS musl lacks the pthread cancellation family, which
            # the ENABLE_CANCELLATION code path requires.  Upstream provides
            # --disable-cancellation for exactly this kind of libc.
            self.output.warning(
                "OHOS musl lacks pthread_setcancelstate/pthread_setcanceltype; "
                "building with cancellation disabled (upstream "
                "--disable-cancellation configuration)"
            )
            cancellation = False
        tc = CMakeToolchain(self)
        tc.variables["RTPI_ENABLE_CANCELLATION"] = cancellation
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # CI workers are shared multi-core devices; cap build parallelism so
        # concurrent jobs cannot exhaust memory (CI build #51104 OOMed).
        # Set via conf (not cmake.build(args=...)) — the args kwarg does not
        # exist in every conan release used by CI workers.
        self.conf.define("tools.build:jobs", 1)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["rtpi"]
        self.cpp_info.set_property("cmake_file_name", "librtpi")
        self.cpp_info.set_property("cmake_target_name", "librtpi::librtpi")
        self.cpp_info.set_property("pkg_config_name", "rtpi")
        # pthread comes from the platform libc (musl on OHOS keeps a
        # libpthread.a stub; glibc needs -lpthread for consumers).
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
