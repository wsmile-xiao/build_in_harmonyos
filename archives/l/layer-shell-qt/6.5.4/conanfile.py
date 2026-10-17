#!/usr/bin/env python3
"""Conan recipe for KDE layer-shell-qt 6.5.4 on HarmonyOS PC."""

import glob
import os
import re
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LayerShellQtConan(ConanFile):
    name = "layer-shell-qt"
    version = "6.5.4"
    description = "Qt component implementing the Wayland wlr-layer-shell protocol"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/plasma/layer-shell-qt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The upstream implementation includes QtWayland private client APIs.
        # qtbase alone supplies Qt6::Gui, but not these private headers.
        self.requires("ecm/6.20.0")
        self.requires("qtbase/6.11.1.2")
        self.requires("qtwayland/6.11.1")
        self.requires("wayland/1.22.0")
        self.requires("libxkbcommon/1.6.0")

    def build_requirements(self):
        self.tool_requires("wayland-protocols/1.36.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["scanner_sources"],
            strip_root=True,
            destination="wayland-scanner-src",
        )
        get(
            self,
            **self.conan_data["expat_sources"],
            strip_root=True,
            destination="expat-src",
        )

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)

        ecm = self.dependencies["ecm"].package_folder
        qtbase = self.dependencies["qtbase"].package_folder
        qtwayland = self.dependencies["qtwayland"].package_folder
        wayland = self.dependencies["wayland"].package_folder
        protocols = self.dependencies.build["wayland-protocols"].package_folder
        static_scanner = os.path.join(self.generators_folder, "wayland-scanner")

        tc.cache_variables.update(
            {
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                # OHOS's loader does not propagate DT_RUNPATH for transitive
                # dependencies; DT_RPATH keeps QtWayland's Wayland libs visible.
                "CMAKE_SHARED_LINKER_FLAGS": "-Wl,--disable-new-dtags",
                "ECM_DIR": os.path.join(ecm, "share", "ECM", "cmake"),
                "Qt6_DIR": os.path.join(qtbase, "lib", "cmake", "Qt6"),
                "Qt6WaylandClient_DIR": os.path.join(
                    qtwayland, "lib", "cmake", "Qt6WaylandClient"
                ),
                "Qt6WaylandClientPrivate_DIR": os.path.join(
                    qtbase, "lib", "cmake", "Qt6WaylandClientPrivate"
                ),
                "WaylandScanner_EXECUTABLE": static_scanner,
                "WaylandProtocols_DATADIR": os.path.join(
                    protocols, "share", "wayland-protocols"
                ),
                # Upstream 6.5.4 uses REQUIRED_QT_VERSION in its Qt 6.10+
                # private-target check; provide the Qt version selected above.
                "REQUIRED_QT_VERSION": "6.11.1",
                "LAYER_SHELL_QT_BUILD_QML": "OFF",
                "QT_BUILD_TESTS": "ON",
                "QT_BUILD_EXAMPLES": "OFF",
            }
        )
        tc.generate()

        # The package .pc files have prefix=/; create build-local relocated
        # copies for ECM's FindWayland/FindWaylandProtocols and pkg-config.
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        os.makedirs(fixed_pc_dir, exist_ok=True)
        pkg_dirs = [
            os.path.join(wayland, "lib", "pkgconfig"),
            os.path.join(protocols, "share", "pkgconfig"),
            os.path.join(self.dependencies["libxkbcommon"].package_folder,
                         "lib", "pkgconfig"),
        ]
        for pkg_dir in pkg_dirs:
            for source_pc in glob.glob(os.path.join(pkg_dir, "*.pc")):
                with open(source_pc, encoding="utf-8") as stream:
                    content = stream.read()
                content = re.sub(
                    r"(?m)^prefix=.*$", f"prefix={os.path.dirname(os.path.dirname(pkg_dir))}", content
                )
                content = re.sub(r"(?m)^Requires\.private:.*$", "", content)
                content = re.sub(r"(?m)^Libs\.private:.*$", "", content)
                with open(
                    os.path.join(fixed_pc_dir, os.path.basename(source_pc)),
                    "w", encoding="utf-8", newline="\n"
                ) as stream:
                    stream.write(content)
        # The .pc copy from wayland/ is dynamic-linked; use our static tool.
        with open(
            os.path.join(fixed_pc_dir, "wayland-scanner.pc"),
            "w", encoding="utf-8", newline="\n"
        ) as stream:
            stream.write(
                f"prefix={self.generators_folder}\n"
                "bindir=${prefix}\n"
                "wayland_scanner=${bindir}/wayland-scanner\n\n"
                "Name: Wayland Scanner\n"
                "Description: Statically linked Wayland scanner\n"
                "Version: 1.22.0\n"
            )

    def _build_environment(self):
        wayland = self.dependencies["wayland"].package_folder
        protocols = self.dependencies.build["wayland-protocols"].package_folder
        env = Environment()
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(protocols, "share", "pkgconfig"))
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(wayland, "lib", "pkgconfig"))
        env.prepend_path("PKG_CONFIG_PATH", fixed_pc_dir)
        for dependency in self.dependencies.host.values():
            if dependency.package_folder:
                libdir = os.path.join(dependency.package_folder, "lib")
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.prepend_path("PATH", os.path.join(wayland, "bin"))
        return env

    def build(self):
        apply_conandata_patches(self)
        expat_static = self._build_static_expat()
        self._build_static_wayland_scanner(expat_static)
        cmake = CMake(self)
        with self._build_environment().vars(self, scope="build").apply():
            cmake.configure()
            cmake.build()
            test_program = os.path.join(
                self.build_folder, "bin", "layershellqt-test"
            )
            # The upstream app test opens windows and exits after five seconds.
            # Offscreen QPA lets it run in the headless CI/PC build environment.
            runtime_libdirs = []
            for dependency in self.dependencies.host.values():
                if dependency.package_folder:
                    libdir = os.path.join(dependency.package_folder, "lib")
                    if os.path.isdir(libdir) and libdir not in runtime_libdirs:
                        runtime_libdirs.append(libdir)
            runtime_ld_path = ":".join(runtime_libdirs)
            self.run(
                f'LD_LIBRARY_PATH="{runtime_ld_path}:${{LD_LIBRARY_PATH:-}}" '
                f'QT_QPA_PLATFORM=offscreen "{test_program}"'
            )

    def _build_static_expat(self):
        # The published expat Conan package is shared-only. Compile the same
        # pinned source as a private static build tool dependency for scanner.
        # GitHub's codeload tag archive preserves the monorepo's expat/ prefix.
        source = os.path.join(self.source_folder, "expat-src", "expat")
        build = os.path.join(self.generators_folder, "expat-static")
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        self.run(
            f'cmake -S "{source}" -B "{build}" '
            f'-DCMAKE_TOOLCHAIN_FILE="{toolchain}" '
            '-DEXPAT_BUILD_TOOLS=OFF -DEXPAT_BUILD_EXAMPLES=OFF '
            '-DEXPAT_BUILD_TESTS=OFF -DEXPAT_BUILD_DOCS=OFF '
            '-DEXPAT_SHARED_LIBS=OFF -DEXPAT_BUILD_PKGCONFIG=OFF '
            '-DEXPAT_WITH_GETRANDOM=ON '
            '-DCMAKE_POSITION_INDEPENDENT_CODE=ON '
            '-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY',
            env="conanbuild",
        )
        self.run(f'cmake --build "{build}" --parallel 2', env="conanbuild")
        candidates = glob.glob(os.path.join(build, "**", "libexpat.a"), recursive=True)
        if not candidates:
            raise RuntimeError("The private static expat build did not produce libexpat.a")
        return candidates[0], source, build

    def _build_static_wayland_scanner(self, expat_static):
        # The shared scanner shipped by wayland/1.22.0 cannot load its Conan
        # cache libraries on HMDFS. Build the same scanner from the pinned
        # upstream source as a static host tool before CMake invokes it.
        source = os.path.join(self.source_folder, "wayland-scanner-src")
        config_h = os.path.join(source, "config.h")
        with open(config_h, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(
                '#define HAVE_EXPAT 1\n'
                '#define PACKAGE "wayland"\n'
                '#define VERSION "1.22.0"\n'
            )

        version_template = os.path.join(source, "src", "wayland-version.h.in")
        version_header = os.path.join(source, "src", "wayland-version.h")
        with open(version_template, encoding="utf-8") as stream:
            version = stream.read()
        for key, value in (
            ("@WAYLAND_VERSION@", "1.22.0"),
            ("@WAYLAND_VERSION_MAJOR@", "1"),
            ("@WAYLAND_VERSION_MINOR@", "22"),
            ("@WAYLAND_VERSION_MICRO@", "0"),
        ):
            version = version.replace(key, value)
        with open(version_header, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(version)

        dtd_header = os.path.join(source, "src", "wayland.dtd.h")
        embed = os.path.join(source, "src", "embed.py")
        dtd = os.path.join(source, "protocol", "wayland.dtd")
        self.run(f'python3 "{embed}" "{dtd}" wayland_dtd > "{dtd_header}"',
                 env="conanbuild")

        expat_library, expat_source, expat_build = expat_static
        scanner = os.path.join(self.generators_folder, "wayland-scanner")
        compiler = shutil.which("clang") or "/data/service/hnp/bin/clang"
        self.run(
            f'{compiler} -o "{scanner}" '
            f'-include "{config_h}" '
            f'-I"{source}" -I"{os.path.join(source, "src")}" '
            f'-I"{os.path.join(source, "protocol")}" '
            f'"{os.path.join(source, "src", "scanner.c")}" '
            f'"{os.path.join(source, "src", "wayland-util.c")}" '
            f'-I"{os.path.join(expat_source, "lib")}" -I"{expat_build}" '
            f'"{expat_library}" -lm -lpthread -static',
            env="conanbuild",
        )
        self.output.info("Built statically linked wayland-scanner for HMDFS")

    def package(self):
        CMake(self).install()

    def package_info(self):
        # Use the upstream installed LayerShellQtConfig/Targets files, which
        # carry the exact Qt target names and transitive link requirements.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = ["lib/cmake"]
        self.cpp_info.libs = ["LayerShellQtInterface"]
