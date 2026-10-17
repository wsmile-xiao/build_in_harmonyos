#!/usr/bin/env python3
"""Conan recipe for ydotool 1.0.4 — generic command-line input automation tool.

ydotool injects keyboard/mouse events through the Linux uinput framework:
  - ydotoold: opens /dev/uinput, creates a persistent virtual input device and
    relays `struct input_event` records received over an AF_UNIX datagram
    socket;
  - ydotool:  client that sends input_event records to that socket
    (click / key / mousemove / type subcommands).
Pure C99, no third-party dependencies (libc only). systemd and scdoc are both
optional upstream: systemd only selects the user-unit install directory, and
scdoc only builds the man pages.

OHOS / HarmonyOS PC adaptation notes:
  - The OHOS native sysroot ships linux/uinput.h and linux/input-event-codes.h
    with struct uinput_setup / UI_DEV_SETUP / UI_DEV_CREATE, so the uinput API
    surface compiles unchanged.
  - Runtime access to /dev/uinput is gated by the platform security policy: on
    HarmonyOS PC a normal user process gets EACCES (the kernel has uinput —
    /proc/misc lists minor 223 — but the device node is not accessible to
    ordinary apps). The daemon therefore cannot create a virtual device
    without system-level privileges. This is a platform boundary, not a build
    defect; test_package covers both the blocked and the accessible branch.
  - The client/daemon channel uses AF_UNIX datagram sockets, and HarmonyOS
    SELinux also denies pathname AF_UNIX bind() (EPERM) to ordinary processes
    (knowledge base E024). test_package probes that capability (A8) and runs
    the byte-level wire-protocol assertions (A9-A15) wherever pathname
    sockets are permitted; on E024-restricted systems they are reported as
    skipped, with the platform reason, instead of failing.
  - Upstream derives VERSION from `git describe`; release tarballs carry no git
    metadata, so patch 0001 adds a packaging override (-DYDOTOOL_VERSION) plus
    a release fallback.
  - Upstream unconditionally runs `scdoc` for the man pages; patch 0002 makes
    the man pages optional when scdoc is absent.
  - Upstream cmake_minimum_required(VERSION 3.4) is rejected by CMake >= 4.0;
    the toolchain injects CMAKE_POLICY_VERSION_MINIMUM=3.5 (no patch needed,
    same approach upstream later adopted for other projects).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class YdotoolConan(ConanFile):
    name = "ydotool"
    version = "1.0.4"
    description = "Generic command-line input automation tool (uinput client + daemon)"
    license = "AGPL-3.0-or-later"
    homepage = "https://github.com/ReimuNotMoe/ydotool"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("automation", "uinput", "input", "cli", "daemon")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # None: libc/libc++ only (POSIX sockets, getopt, epoll, uinput ioctls).
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4.0 removed compatibility with cmake_minimum_required < 3.5;
        # upstream declares 3.4, so raise the policy floor (source untouched).
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Feed the packaged version into patch 0001: a release tarball has no
        # git metadata, so `git describe` cannot provide the version string.
        tc.variables["YDOTOOL_VERSION"] = self.version
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream installs the binaries (and the systemd unit template); ship
        # the AGPL license text as required by the license.
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
