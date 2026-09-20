#!/usr/bin/env python3
"""Conan recipe for libkscreen 6.7.2 on HarmonyOS PC.

libkscreen is the KDE Plasma screen management library (KF6Screen /
KF6ScreenDpms + the kscreen-doctor CLI and the kscreen_backend_launcher
D-Bus service).

Upstream hard requirements: Qt6 (Core/DBus/Gui/Test/WaylandClient +
GuiPrivate), ECM, PlasmaWaylandProtocols 1.21+, Wayland 1.24 (Client).
XCB (XRandR backend) is optional upstream.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    is not in the KDE platform list)
  - plasma-wayland-protocols is NOT published to the ohpcd registry. The
    recipe therefore requires the upstream plasma-wayland-protocols 1.21
    tarball as a second source, extracts it, and passes its data/
    directory as PLASMA_WAYLAND_PROTOCOLS_DIR so the CMake package check
    succeeds without the missing conan package.
  - wayland/1.22.0 is used instead of the upstream Wayland 1.24 minimum:
    qtbase/6.11.1.2 and qtwayland/6.11.1 both pin wayland/1.22.0 and
    mixing versions is a graph conflict; libkscreen only uses the stable
    Wayland::Client API that 1.22 already provides.
  - XCB is not available on OHOS: patches/0001 makes the XRandR backend
    and the XCB/wayland DPMS helpers conditional. The kwayland backend
    (KSC_KWayland plugin) and KF6Screen core library are still built.
  - BUILD_TESTING=OFF during the conan build; the upstream QTest suite is
    executed separately (see notes.md) because it needs a D-Bus session.
  - Dependencies: qtbase/6.11.1.2, qtwayland/6.11.1, wayland/1.22.0,
    ecm/6.26.0 (build tool)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibkscreenConan(ConanFile):
    name = "libkscreen"
    version = "6.7.2"
    description = "KDE Plasma screen management library (KF6Screen)"
    license = "LGPL-2.1-or-later AND BSD-3-Clause AND GPL-2.0-or-later"
    homepage = "https://invent.kde.org/plasma/libkscreen"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 6.11.1.2 provides Qt6WaylandClient and qt_add_dbus_interface support
        # wayland/1.22.0 (not 1.24.0): qtbase/6.11.1.2 and qtwayland/6.11.1
        # both require wayland/1.22.0; mixing 1.24.0 triggers a version
        # conflict in the graph. Upstream's Wayland 1.24 minimum only guards
        # API added in 1.23+ which libkscreen does not use (it only links
        # Wayland::Client the same way qtwayland does).
        self.requires("qtbase/6.11.1.2")
        self.requires("qtwayland/6.11.1")
        self.requires("wayland/1.22.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        # Qt6LinguistTools (lrelease + Qt6::LinguistTools CMake module) is
        # required by ECMPoQmTools for the upstream poqm translation step
        # (ecm_install_po_files_as_qm). Published on ohpcd as
        # qt6linguisttools/6.11.1; consumed as a build requirement (R36).
        self.tool_requires("qt6linguisttools/6.11.1")
        # wayland-scanner is needed at build time to generate the KDE
        # protocol client sources; the wayland conan package ships the
        # scanner binary (arm64, runs natively on this host).
        self.tool_requires("wayland/1.22.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # First source entry = the libkscreen tarball (strip_root=True).
        get(self, **self.conan_data["sources"], strip_root=True)
        # Second source = plasma-wayland-protocols 1.21 (the minimum version
        # accepted by upstream find_package(PlasmaWaylandProtocols 1.21)).
        # The ohpcd registry has no plasma-wayland-protocols package, so the
        # protocol XMLs are carried alongside and pointed to explicitly.
        pwp = self.conan_data["plasma_wayland_protocols"]
        get(self, **pwp, strip_root=True,
            destination=os.path.join(self.source_folder, "plasma-wayland-protocols"))
    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # XCB is not available on OHOS; the patch makes the XRandR backend
        # and XCB DPMS helper conditional on XCB being found.
        tc.variables["ENABLE_XRANDR_TESTS"] = "OFF"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # Qt6Config.cmake resolves COMPONENTS relative to Qt6_DIR (qtbase),
        # so find_package(Qt6 COMPONENTS LinguistTools) would look inside
        # qtbase's lib/cmake and fail. Pin Qt6LinguistTools_DIR explicitly
        # (kdbusaddons 6.29.0 precedent).
        ltt = self.dependencies.build.get("qt6linguisttools")
        if ltt:
            tc.variables["Qt6LinguistTools_DIR"] = os.path.join(
                ltt.package_folder, "lib", "cmake", "Qt6LinguistTools"
            )

        # WaylandScanner: ECM's FindWaylandScanner falls back to pkg-config
        # (wayland-scanner.pc) which is not on the search path; pin the
        # executable from the qtbase libexec dir (it was found there by CMake
        # in earlier configure attempts) with the wayland/1.22.0 package's
        # scanner as a secondary candidate.
        qtbase = self.dependencies.get("qtbase")
        qtwayland = self.dependencies.get("qtwayland")
        wayland = self.dependencies.get("wayland")
        scanner_candidates = []
        if qtbase and qtbase.package_folder:
            scanner_candidates.append(
                os.path.join(qtbase.package_folder, "libexec", "wayland-scanner")
            )
        wl_pkg = wayland.package_folder if wayland else None
        if wl_pkg:
            scanner_candidates.append(os.path.join(wl_pkg, "bin", "wayland-scanner"))
        for cand in scanner_candidates:
            if os.path.isfile(cand):
                tc.variables["WaylandScanner_EXECUTABLE"] = cand
                break

        # plasma-wayland-protocols: provide the directory containing the
        # protocol XMLs plus a pkg-config file so the upstream
        # find_package(PlasmaWaylandProtocols 1.21 CONFIG) succeeds.
        pwp_dir = os.path.join(self.source_folder, "plasma-wayland-protocols")
        tc.variables["PLASMA_WAYLAND_PROTOCOLS_DIR"] = os.path.join(pwp_dir, "src", "protocols")

        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # Add every dependency's lib/cmake dir so find_package(Qt6*) and
            # the PlasmaWaylandProtocols CONFIG search all resolve.
            # Skip the OLD qtbase/6.11.1: the qt6linguisttools -> qttools
            # tool chain pulls it in, but it ships neither Qt6DBus nor
            # Qt6WaylandClient; it must never win the Qt6_DIR lookup
            # (PREPEND means later lines end up FIRST, so it would shadow
            # qtbase/6.11.1.2 which does provide those components).
            qtbase_new = qtbase.package_folder if qtbase else None
            for dep in self.dependencies.values():
                if not dep or not dep.package_folder:
                    continue
                try:
                    dep_ref = str(dep.ref)
                except Exception:
                    dep_ref = ""
                if dep_ref == "qtbase/6.11.1":
                    continue
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
            # PlasmaWaylandProtocols is not a conan package; expose it as a
            # CMake CONFIG package from the extracted source tree.
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pwp_dir}")')
            if ltt:
                lines.append(
                    f'set(Qt6LinguistTools_DIR '
                    f'"{os.path.join(ltt.package_folder, "lib", "cmake", "Qt6LinguistTools")}")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{os.path.join(ltt.package_folder, "lib", "cmake", "Qt6LinguistTools")}")'
                )
            lines.append(
                f'set(PLASMA_WAYLAND_PROTOCOLS_DIR '
                f'"{os.path.join(pwp_dir, "src", "protocols")}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            # Re-assert qtbase/6.11.1.2 LAST so it wins the Qt6_DIR lookup:
            # list(PREPEND) puts the last entry first.
            lines.append(f'set(Qt6_DIR "{qt_pkg}/lib/cmake/Qt6")')
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")'
            )
            if qtwayland and qtwayland.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{qtwayland.package_folder}/lib/cmake")'
                )
            if wayland and wayland.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{wayland.package_folder}/lib/cmake")'
                )
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

        # The conan toolchain pins CMAKE_CXX_STANDARD=17 via a plain set()
        # executed at CMAKE_PROJECT_INCLUDE time, which always shadows the
        # project's own cache-level CMAKE_CXX_STANDARD (karchive 6.26.0
        # precedent). libkscreen needs C++20 (operator<=>); rewrite the
        # value directly in the generated conan_toolchain.cmake.
        toolchain_cmake = os.path.join(
            self.generators_folder, "conan_toolchain.cmake"
        )
        if os.path.isfile(toolchain_cmake):
            with open(toolchain_cmake, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace(
                "set(CMAKE_CXX_STANDARD 17)", "set(CMAKE_CXX_STANDARD 20)"
            )
            with open(toolchain_cmake, "w", encoding="utf-8") as f:
                f.write(content)

        # Write a minimal PlasmaWaylandProtocolsConfig.cmake + Version file
        # into the generators folder so find_package() in the project sees
        # the same PLASMA_WAYLAND_PROTOCOLS_DIR we pass above.
        gen = self.generators_folder
        pwp_dir = os.path.join(self.source_folder, "plasma-wayland-protocols")
        with open(os.path.join(gen, "PlasmaWaylandProtocolsConfig.cmake"), "w") as f:
            f.write(
                'set(PLASMA_WAYLAND_PROTOCOLS_DIR '
                f'"{os.path.join(pwp_dir, "src", "protocols")}")\n'
            )
        with open(os.path.join(gen, "PlasmaWaylandProtocolsConfigVersion.cmake"), "w") as f:
            f.write(
                "set(PACKAGE_VERSION 1.21.0)\n"
                "set(PACKAGE_VERSION_EXACT FALSE)\n"
                "set(PACKAGE_VERSION_COMPATIBLE TRUE)\n"
                "set(PACKAGE_VERSION_UNSUITABLE FALSE)\n"
            )

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6ScreenConfig.cmake with proper
        # dependency tracking. Use cmake_find_mode=none so CMakeDeps doesn't
        # shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Screen", "KF6ScreenDpms"]
