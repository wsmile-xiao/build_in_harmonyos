#!/usr/bin/env python3
"""Conan test_package — isc-kea 3.0.3 (consumer view).

Builds and runs real consumers of the packaged artefacts: the kea-dhcp4
server binary linked against the packaged Kea libraries (``--version`` proves
the executable and its whole DT_NEEDED closure load and run), plus a C++
consumer that links the packaged libraries and exercises the public API
(IOAddress round-trip, Element JSON parsing) the way an embedded consumer
does.

A second, HarmonyOS-specific check (``test_ohos_platform``) verifies the parts
of the delivery that only exist for OHOS: the aarch64 / musl / libc++ ABI
signature of a packaged library, that the OHOS loader maps it with
RTLD_NOW, and that the OHOS-only consumer define the package exports
(``BOOST_SP_NO_PTHREAD_SETCANCELSTATE``) reaches the consumer compile line.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class IscKeaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: consumer test skipped")
            return
        bindir = self.cpp.build.bindirs[0]
        pkg = self.dependencies[self.tested_reference_str].package_folder

        # 1) The packaged servers themselves: the Kea daemons take the
        #    single-dash -v (their getopt parser rejects the GNU --version
        #    form); a successful run proves the executable plus the whole
        #    packaged libkea-* closure loads and runs on the target (daemon
        #    traffic needs live sockets, which the test environment cannot
        #    provide).
        for daemon in ("kea-dhcp4", "kea-dhcp6", "kea-dhcp-ddns",
                       "kea-ctrl-agent", "kea-lfc"):
            self.run('"{}/bin/{}" -v'.format(pkg, daemon), env="conanrun")

        # 2) API consumer of the packaged libraries.
        self.run('"{}/test_isc_kea"'.format(bindir), env="conanrun")

        # 3) HarmonyOS-specific platform checks on a packaged library.
        library = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "lib", "libkea-asiolink.so")
        self.run('"{}/test_ohos_platform" "{}"'.format(bindir, library),
                 env="conanrun")
