#!/usr/bin/env python3
"""Conan recipe for Intel PCM (Platform Characterization Monitor) 202502 on HarmonyOS PC.

Upstream pcm targets Intel x86 CPUs: CPU identification goes through the CPUID
instruction, the cycle counter through RDTSC/RDTSCP, and the Linux build uses
the glibc-only ``pthread_getaffinity_np()`` / ``pthread_setaffinity_np()``
extensions.  HarmonyOS PC is aarch64 with a musl-derived libc, so four
portability patches keep the delivery honest:

* 0001 - ``pcm_cpuid()`` executes CPUID on x86 only and otherwise reports the
  reserved zero leaf, so no Intel CPU identity is ever fabricated;
* 0002 - ``RDTSC()`` / ``RDTSCP()`` read the architectural AArch64 virtual
  counter ``CNTVCT_EL0`` (``TPIDR_EL0`` for the auxiliary value);
* 0003 - ``TemporalThreadAffinity`` uses the POSIX ``sched_getaffinity()`` /
  ``sched_setaffinity()`` interfaces that every libc provides;
* 0004 - ``pthread_cancel()`` availability becomes a configure-time feature
  probe and the destructor reports the limitation instead of failing to build.

The upstream Linux feature set is kept: the perfmon uncore discovery, the
daemon/client pair and the sensor server are all built.  ``pcm-raw`` keeps its
simdjson-based event parsing because ``simdjson`` is consumed as a published
Conan dependency, and ``pcm-sensor-server`` keeps its OpenSSL support.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PcmConan(ConanFile):
    name = "pcm"
    version = "202502"
    description = "Intel Platform Characterization Monitor: a portable API and tools to monitor performance and energy metrics"
    license = "BSD-3-Clause"
    homepage = "https://github.com/intel/pcm"
    url = "https://github.com/intel/pcm"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        # E092: CMakeToolchain maps OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, which
        # CMake does not know, so UNIX/LINUX stay false and upstream's
        # if(UNIX) blocks vanish.  The recipe configures with CMAKE_SYSTEM_NAME
        # "Linux" instead (the same workaround as jthread-lite, json11 and
        # qxlsx in this repository); HarmonyOS PC runs a Linux kernel and a
        # musl libc, which is what those upstream branches describe.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pcm supports Linux and OHOS targets, got {self.settings.os}"
            )

    def requirements(self):
        # pcm-raw parses the Intel perfmon event JSON with the simdjson DOM API.
        # The upstream release tarball ships src/simdjson as an empty submodule
        # directory, so the dependency has to come from the artifact registry.
        self.requires("simdjson/3.9.5")
        # pcm-sensor-server enables OpenSSL support by default and only falls
        # back to the plaintext socket protocol when find_package(OpenSSL)
        # fails.  Keep that default instead of narrowing the daemon.
        self.requires("openssl/3.0.21")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Upstream still declares cmake_minimum_required(VERSION 3.5); CMake 4
        # dropped compatibility with anything older, so the policy floor is
        # pinned explicitly instead of patching the upstream project file.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Upstream installs its command line tools into CMAKE_INSTALL_SBINDIR.
        # Conan consumers expect them in the standard bindir, and the shell
        # helper script pcm-bw-histogram is installed to the same place.
        tc.cache_variables["CMAKE_INSTALL_SBINDIR"] = "bin"
        # AddressSanitizer is upstream's default-on option but it needs a
        # sanitizer runtime that the OHOS image does not ship.
        tc.cache_variables["PCM_NO_ASAN"] = "ON"
        tc.cache_variables["PCM_NO_STATIC_LIBASAN"] = "ON"
        tc.cache_variables["PCM_BUILD_EXECUTABLES"] = "ON"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream ships one real test program: tests/daemon_alignment_test
        # verifies that the daemon shared state stays 64-byte aligned for the
        # host page size.  It is architecture independent and is executed here
        # so the upstream test really runs inside the build phase.
        daemon_test = os.path.join(
            self.build_folder, "bin", "tests", "daemon_alignment_test"
        )
        if os.path.isfile(daemon_test):
            self.run(f'"{daemon_test}"', env="conanbuild")
        else:
            self.output.warning(
                "upstream daemon_alignment_test was not built; skipping upstream test"
            )

    def package(self):
        CMake(self).install()

    def package_info(self):
        # Upstream's install rules ship the command line tools, the perfmon
        # opcode tables, the PMU register declarations and the documentation.
        # The libpcm.a / libpcm.so targets are build-time only upstream, so no
        # library is exported here either.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
