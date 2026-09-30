#!/usr/bin/env python3
"""Conan recipe for plasma-wayland-protocols 1.14.0 on HarmonyOS PC (aarch64).

plasma-wayland-protocols ships the XML descriptions of the non-standard Wayland
protocols used by Plasma.  It is a **data-only** package: nothing is compiled or
linked.  Upstream installs

  * the 30 protocol XML files into ${KDE_INSTALL_DATADIR}/plasma-wayland-protocols
    plus two backward-compatibility renames:
      org-kde-plasma-virtual-desktop.xml -> plasma-virtual-desktop.xml
      zkde-screencast-unstable-v1.xml    -> screencast.xml
    (kwayland 5.116 literally consumes `plasma-virtual-desktop.xml`, so the
    rename MUST be preserved -- it is part of the upstream install rules).
  * PlasmaWaylandProtocolsConfig.cmake + PlasmaWaylandProtocolsConfigVersion.cmake
    into ${KDE_INSTALL_CMAKEPACKAGEDIR}/PlasmaWaylandProtocols, whose body defines
    PLASMA_WAYLAND_PROTOCOLS_DIR.

Downstream kwayland5/5.116.0 does
    find_package(PlasmaWaylandProtocols 1.9.0 CONFIG REQUIRED)
and then consumes ${PLASMA_WAYLAND_PROTOCOLS_DIR}/<protocol>.xml for ~22
protocols (appmenu, blur, contrast, dpms, fake-input, fullscreen-shell, idle,
keystate, output-management, outputdevice, plasma-shell, plasma-virtual-desktop,
plasma-window-management, remote-access, server-decoration-palette,
server-decoration, shadow, slide, surface-extension, text-input,
text-input-unstable-v2, wayland-eglstream-controller).

OHOS-specific notes:
  - package_type = "build-scripts": the package has no compiled output, so it is
    not a library and carries no commands (R38: no bin/ => no commands.json).
  - package_id() calls self.info.clear(): a single package ID across toolchains
    (pure data, no ABI), so every consumer shares the same package.
  - R32: settings.os is never compared, so no "Linux"/"OHOS" branching is needed.
  - R33: no bare shell compiler variables -- all build flags come from the Conan
    CMakeToolchain.
  - The upstream install puts the native CMake package config under
    ${KDE_INSTALL_CMAKEPACKAGEDIR} = <prefix>/lib/cmake; package_info() exposes
    that dir via cpp_info.builddirs and sets cmake_find_mode="none" so CMakeDeps
    does NOT emit a shadowing PlasmaWaylandProtocolsConfig.cmake.  The upstream
    (native) config is therefore the one a consumer's find_package() resolves, and
    its PLASMA_WAYLAND_PROTOCOLS_DIR points *inside this conan package*
    (libkscreen/6.7.2 and karchive/6.26.0 precedent).
  - Build tool: extra-cmake-modules (ECM) 6.26.0 as tool_requires; it provides
    KDEInstallDirs / ECMSetupVersion used by the upstream CMakeLists.txt.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PlasmaWaylandProtocolsConan(ConanFile):
    name = "plasma-wayland-protocols"
    version = "1.14.0"
    description = ("XML descriptions of the non-standard Wayland protocols "
                   "used by Plasma")
    license = "LGPL-2.1-or-later AND BSD-3-Clause"
    homepage = "https://invent.kde.org/libraries/plasma-wayland-protocols"
    url = "https://invent.kde.org/libraries/plasma-wayland-protocols"

    package_type = "build-scripts"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # Data-only package: no ABI, one package ID for every toolchain.
        self.info.clear()

    def layout(self):
        cmake_layout(self)

    def build_requirements(self):
        # ECM provides KDEInstallDirs / ECMSetupVersion / CMakePackageConfigHelpers
        # glue used by the upstream CMakeLists.txt.  Published on ohpcd as
        # ecm/6.26.0 (W0: recipe confirmed published to the ohpcd registry).
        self.tool_requires("ecm/6.26.0")

    def source(self):
        # R39: the official download.kde.org source is present in the list; a
        # measured-reachable mirror is listed first because the CI mirror
        # fallback does not cover download.kde.org.  All URLs ship the same
        # byte-identical tarball, verified by the single sha256 below.
        entry = self.conan_data["sources"]
        urls = entry["url"]
        if not isinstance(urls, list):
            urls = [urls]
        last_error = None
        for url in urls:
            try:
                get(self, url=url, sha256=entry["sha256"], strip_root=True)
                self.output.info(f"plasma-wayland-protocols: source fetched from {url}")
                return
            except Exception as exc:  # try the next mirror URL
                last_error = exc
                self.output.warning(
                    f"plasma-wayland-protocols: source URL failed ({url}): {exc}")
        raise Exception(f"plasma-wayland-protocols: all source URLs failed: {last_error}")

    def generate(self):
        tc = CMakeToolchain(self)
        # Pure data project (no compiled targets): skip the cross-compiler probe
        # so a missing/incompatible clang cannot fail the configure step.
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_CXX_COMPILER_WORKS"] = "1"
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream install rules ship neither license file.
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.txt", src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses", "LICENSES"))

    def package_info(self):
        # Data-only: no headers, no libs.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # The package ships its own PlasmaWaylandProtocolsConfig.cmake.  Tell
        # CMakeDeps not to generate a shadowing config file, and expose the
        # native config dir on CMAKE_PREFIX_PATH (through builddirs) so a
        # consumer's find_package(PlasmaWaylandProtocols CONFIG REQUIRED)
        # resolves it and gets PLASMA_WAYLAND_PROTOCOLS_DIR.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
