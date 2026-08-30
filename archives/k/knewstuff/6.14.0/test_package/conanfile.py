#!/usr/bin/env python3
"""Conan test_package for knewstuff 6.14.0 — real API execution (R34).

KF6NewStuffConfig / KF6NewStuffCoreConfig do find_dependency() on the whole
direct-dependency set, so mirror it here and expose every dep's lib/cmake.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KnewstuffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("qtbase-gui/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("karchive/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kpackage/6.18.0")
        self.requires("attica/6.18.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Qt6 split-package components (Qml/Quick/QuickWidgets from
        # qtdeclarative, Gui/Widgets from qtbase-gui) resolve via
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH; see main recipe comment.
        qt_extra = [
            dep.package_folder for dep in self.dependencies.values()
            if dep and dep.package_folder
            and os.path.isdir(os.path.join(dep.package_folder, "lib", "cmake"))
            and any(n.startswith("Qt6") for n in os.listdir(
                os.path.join(dep.package_folder, "lib", "cmake")))
        ]
        if qt_extra:
            tc.cache_variables[
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)
        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                # package root too: split Qt6 configs live under
                # <pkg>/lib/cmake/Qt6Qml/ (needs <pkg> on the prefix path)
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
            f'list(PREPEND CMAKE_PREFIX_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _all_dep_folders(self):
        # self.dependencies.values() only yields DIRECT requirements;
        # qtbase-gui / transitive KF6 libs would be missed. Walk the host
        # graph recursively (dedup by package_folder).
        seen, out = set(), []
        stack = list(self.dependencies.host.values())
        while stack:
            dep = stack.pop()
            if not dep:
                continue
            try:
                sub = list(dep.dependencies.host.values())
            except Exception:  # noqa: BLE001
                sub = []
            stack.extend(sub)
            pf = getattr(dep, "package_folder", None)
            if pf and pf not in seen:
                seen.add(pf)
                out.append(pf)
        return out

    def test(self):
        # Published KF6/Qt6 binaries embed ../../bin/*.so relative DT_NEEDED;
        # mirror them via symlink farm reachable from the test CWD parents
        # (kxmlgui/ktextwidgets pattern).
        libdirs = self._all_dep_folders()
        for up in ("..", os.path.join("..", "..")):
            tp_bin = os.path.abspath(os.path.join(self.build_folder, up, "bin"))
            os.makedirs(tp_bin, exist_ok=True)
            for pf in libdirs:
                libdir = os.path.join(pf, "lib")
                if os.path.isdir(libdir):
                    for name in os.listdir(libdir):
                        if name.startswith("libKF6") and ".so" in name:
                            link = os.path.join(tp_bin, name)
                            if not os.path.lexists(link):
                                try:
                                    os.symlink(
                                        os.path.join(libdir, name), link)
                                except OSError:
                                    pass

        env = Environment()
        libpaths = [os.path.join(pf, "lib") for pf in libdirs]
        # prepend_path (not append) with an os.pathsep-joined string:
        # Environment.append(name, LIST) would stringify the python list.
        env.prepend_path("LD_LIBRARY_PATH", os.pathsep.join(libpaths))
        self.output.info(f"TEST RUN LD dirs ({len(libpaths)})")
        for probe in ("libQt6Widgets.so.6", "libQt6Core.so.6"):
            found = next((p for p in libpaths if os.path.exists(
                os.path.join(p, probe))), None)
            self.output.info(f"probe {probe}: {found or 'MISSING'}")
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            bindir = os.path.abspath(self.cpp.build.bindir)
            exe = os.path.join(bindir, "test_knewstuff")
            # cwd MUST be the dir containing the exe: our own
            # libKF6NewStuffWidgets.so embeds a relative DT_NEEDED
            # '../../bin/libKF6NewStuffCore.so' (KF6 libs ship without
            # SONAME, so CMake records the in-build path), and musl
            # resolves slash-containing NEEDEDs against the process CWD —
            # exactly where the ../../bin farm above was created.
            self.run(f'"{exe}"', cwd=bindir)
