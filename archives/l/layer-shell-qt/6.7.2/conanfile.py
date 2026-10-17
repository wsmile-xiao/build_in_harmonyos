#!/usr/bin/env python3
"""Conan recipe for layer-shell-qt 6.7.2 on HarmonyOS PC.

layer-shell-qt is the KDE Plasma QtWayland client extension implementing
the wlr-layer-shell protocol (LayerShellQt library and the
QWaylandLayerShellIntegration plugin).

Upstream requirements: Qt6 (WaylandClient/Qml), ECM, WaylandScanner,
Wayland (Client/Server), WaylandProtocols, xkbcommon.

OHOS-specific adaptations (mirroring the libkscreen 6.7.2 Plasma recipe):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project's
    CMakeLists.txt relies on.
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH.
  - WaylandScanner_EXECUTABLE pinned from the qtbase libexec dir
    (khronos wayland-scanner is not shipped on OHOS as a standalone tool).
  - Dependencies: qtbase/6.11.1.2, qtwayland/6.11.1, wayland/1.22.0,
    wayland-protocols/1.36, libxkbcommon/1.6.0, ecm/6.26.0 (tool_require).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LayerShellQtConan(ConanFile):
    name = "layer-shell-qt"
    version = "6.7.2"
    description = "KDE Plasma - QtWayland client shell integration (LayerShellQt)"
    license = "BSD-3-Clause"
    homepage = "https://invent.kde.org/plasma/layer-shell-qt"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtwayland/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("wayland/1.22.0")
        self.requires("wayland-protocols/1.36")
        self.requires("libxkbcommon/1.6.0")
        # Override qtbase version to resolve conflict between qtwayland
        # (needs 6.11.1.2 for Qt6WaylandClient) and qtdeclarative (pins 6.11.1).
        self.requires("qtbase/6.11.1.2", override=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        # ECM module path (CMakeDeps-generated ECMConfig.cmake does not
        # propagate ECM_MODULE_PATH).
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # WaylandScanner executable: prefer qtbase libexec, fall back to the
        # wayland package bin dir (libkscreen precedent).
        qtbase = self.dependencies.get("qtbase")
        wayland = self.dependencies.get("wayland")
        for cand in [
            os.path.join(qtbase.package_folder, "libexec", "wayland-scanner"),
            os.path.join(wayland.package_folder, "bin", "wayland-scanner"),
        ]:
            if cand and os.path.isfile(cand):
                tc.variables["WaylandScanner_EXECUTABLE"] = cand
                break

        # WaylandProtocols: the installed wayland-protocols.pc hardcodes an
        # old build machine cache path (.cache/conan2/p/b/...) whose staging
        # XML files do not exist locally -> ECM FindWaylandProtocols.cmake
        # resolves pkgdatadir via pkg-config (pkg_get_variable) and CMake
        # fails at make time on "No rule to make target
        # .../staging/xdg-activation/xdg-activation-v1.xml".
        # Fix: regenerate wayland-protocols.pc with the real package prefix
        # and put it first on PKG_CONFIG_PATH (E537-adjacent relocatable fix).
        wp = self.dependencies.get("wayland-protocols")
        if wp and wp.package_folder:
            wp_pkgconf = os.path.join(self.build_folder, "pkgconfig-fixed")
            os.makedirs(wp_pkgconf, exist_ok=True)
            wp_pc = os.path.join(wp_pkgconf, "wayland-protocols.pc")
            if not os.path.exists(wp_pc):
                with open(wp_pc, "w") as fh:
                    fh.write(
                        f"prefix={wp.package_folder}\n"
                        "datarootdir=${prefix}/share\n"
                        "pkgdatadir=${datarootdir}/wayland-protocols\n"
                        "\n"
                        "Name: Wayland Protocols\n"
                        "Description: Wayland protocol files\n"
                        "Version: 1.36\n"
                    )
            wp_env = Environment()
            wp_env.prepend_path("PKG_CONFIG_PATH", wp_pkgconf)
            wp_env.vars(self, scope="build").save_script(
                "conanbuild_wp_pkgconfig"
            )
            tc.cache_variables["WaylandProtocols_DATADIR"] = os.path.join(
                wp.package_folder, "share", "wayland-protocols"
            )

        # Qt6 split-package component discovery: qtbase's top-level
        # lib/cmake/Qt6/Qt6Config.cmake resolves REQUIRED COMPONENTS (Qml,
        # Quick from qtdeclarative; WaylandClient from qtwayland) only
        # against QT_ADDITIONAL_PACKAGES_PREFIX_PATH (knewstuff precedent).
        qt_extra = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                if os.path.isdir(
                        os.path.join(dep.package_folder, "lib", "cmake")) and \
                   any(n.startswith("Qt6") for n in os.listdir(
                       os.path.join(dep.package_folder, "lib", "cmake"))):
                    qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables[
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

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
            for dep in self.dependencies.values():
                if not dep or not dep.package_folder:
                    continue
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}")'
                )
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
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def _fix_xkb_pkgconfig(self):
        """Regenerate xkbcommon.pc with the correct package prefix."""
        xkb = self.dependencies.get("libxkbcommon")
        if not xkb or not xkb.package_folder:
            return
        pkgconf_dir = os.path.join(self.build_folder, "pkgconfig-fixed")
        os.makedirs(pkgconf_dir, exist_ok=True)
        pc_path = os.path.join(pkgconf_dir, "xkbcommon.pc")
        if not os.path.exists(pc_path):
            with open(pc_path, "w") as fh:
                fh.write(
                    f"prefix={xkb.package_folder}\n"
                    "includedir=${prefix}/include\n"
                    "libdir=${prefix}/lib\n"
                    "\n"
                    "Name: xkbcommon\n"
                    "Description: XKB API common to servers and clients\n"
                    "Version: 1.6.0\n"
                    "Libs: -L${libdir} -lxkbcommon\n"
                    "Cflags: -I${includedir}\n"
                )
        return pkgconf_dir

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own LayerShellQtConfig.cmake; use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["LayerShellQtInterface"]
