#!/usr/bin/env python3
"""Conan test_package for kirigami2 5.116.0 on HarmonyOS PC.

Validates the three consumption dimensions:
  * C++ consumer: links KF5::Kirigami2 and reads the exported
    Kirigami2::Units meta object.
  * QML consumer: asserts the installed QML module
    ``lib/qml/org/kde/kirigami`` carries ``qmldir`` + the plugin .so and
    drives a real QQmlEngine import of ``org.kde.kirigami`` (R34/R40 —
    offscreen QPA, no display required).
  * HarmonyOS-specific: ``__OHOS__``/uname/aarch64 assertions plus the
    Kirigami2 Units API (rule12 HarmonyOS-specific test row).
"""
import glob
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment

# The installed QML modules of the runtime dependencies must be on the
# QML import path for the org.kde.kirigami probe (QtQuick.Controls 2,
# QtGraphicalEffects).
_QML_DEPENDENCIES = (
    "qt5-qtdeclarative",
    "qt5-qtquickcontrols2",
    "qt5-qtgraphicaleffects",
    "qt5-qtbase",
)


class Kirigami2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Mirror the kirigami2 recipe: force the graph onto
        # qt5-qtbase/5.15.2.2 (the qt5-qtsvg pin otherwise resolves
        # 5.15.2, and the mismatched package ids break the graph).
        self.requires("qt5-qtbase/5.15.2.2", override=True)
        self.requires("qt5-qtdeclarative/5.15.2")
        self.requires("qt5-qtquickcontrols2/5.15.2")
        self.requires("qt5-qtsvg/5.15.2.1")
        self.requires("qt5-qtgraphicaleffects/5.15.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        if str(self.settings.os) == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = compilers.get("cpp") or compilers.get("cxx")
            if compiler:
                compiler_dir = os.path.dirname(os.path.realpath(compiler))
                tc.variables["OHOS_CXX_RUNTIME_DIR"] = os.path.join(
                    compiler_dir, "..", "lib", "aarch64-linux-ohos"
                )
        # Order matters: the fixed qtbase tree must be staged BEFORE the
        # paths file is written (the paths file puts the staged prefix
        # first so find_package(Qt5Core) resolves the fixed copy).
        self._stage_fixed_qtbase_cmake()
        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()
        self._install_qt5_shims()

    def _install_qt5_shims(self):
        """Overwrite the CMakeDeps-generated Qt5Config.cmake with a bridge
        that dispatches the Qt5 umbrella find_package across the qt5-*
        package split, and install the Qt5QuickTest shim — same approach
        as the kirigami2 recipe generate() step."""
        qtbase = self.dependencies["qt5-qtbase"]
        staged_root = os.path.join(self.generators_folder, "qt5base-cmake-fixed")
        qtbase_prefix = staged_root if os.path.isdir(staged_root) else qtbase.package_folder
        qtbase_prefix = qtbase_prefix.replace("\\", "/")

        bridge = os.path.join(self.generators_folder, "Qt5Config.cmake")
        with open(bridge, "w", encoding="utf-8") as f:
            f.write(
                "# Auto-generated Qt5 umbrella bridge for the Conan qt5-*\n"
                "# package split (test_package flavour).\n"
                "set(_qt5_bridge_base \"Core;Gui;Concurrent;Test;Widgets;Network;OpenGL;PrintSupport;Xml;Sql;DBus\")\n"
                "set(_Qt5_BRIDGE_REQUESTED ${Qt5_FIND_COMPONENTS})\n"
                "set(Qt5_FIND_COMPONENTS \"\")\n"
                "foreach(_comp ${_Qt5_BRIDGE_REQUESTED})\n"
                "    if(_comp IN_LIST _qt5_bridge_base)\n"
                "        list(APPEND Qt5_FIND_COMPONENTS ${_comp})\n"
                "    endif()\n"
                "endforeach()\n"
                "if(Qt5_FIND_COMPONENTS)\n"
                f'    include("{qtbase_prefix}/lib/cmake/Qt5/Qt5Config.cmake")\n'
                "endif()\n"
                "set(Qt5_FIND_COMPONENTS ${_Qt5_BRIDGE_REQUESTED})\n"
                "# Cross-package components resolve through their own\n"
                "# CMakeDeps/native configs (already on CMAKE_PREFIX_PATH).\n"
                "foreach(_comp Qml Quick QuickTest QuickControls2 QuickTemplates2 Svg)\n"
                "    if(\"${_comp}\" IN_LIST Qt5_FIND_COMPONENTS AND NOT TARGET Qt5::${_comp})\n"
                "        if(\"${_comp}\" STREQUAL \"Qml\")\n"
                "            find_package(Qt5Qml QUIET)\n"
                "            if(Qt5Qml_FOUND AND NOT TARGET Qt5::Qml)\n"
                "                message(WARNING \"Qt5Qml config found but Qt5::Qml target missing\")\n"
                "            endif()\n"
                "        elseif(\"${_comp}\" STREQUAL \"Quick\" OR \"${_comp}\" STREQUAL \"QuickTest\")\n"
                "            find_package(Qt5Qml QUIET)\n"
                "            if(NOT TARGET Qt5::${_comp})\n"
                "                add_library(Qt5::${_comp} INTERFACE IMPORTED)\n"
                "                set_target_properties(Qt5::${_comp} PROPERTIES\n"
                "                    INTERFACE_LINK_LIBRARIES Qt5::Qml)\n"
                "            endif()\n"
                "        elseif(\"${_comp}\" STREQUAL \"QuickControls2\" OR \"${_comp}\" STREQUAL \"QuickTemplates2\")\n"
                "            find_package(Qt5${_comp} QUIET)\n"
                "        elseif(\"${_comp}\" STREQUAL \"Svg\")\n"
                "            find_package(Qt5Svg QUIET)\n"
                "            if(NOT TARGET Qt5::Svg AND TARGET Qt5::Svg_)\n"
                "            endif()\n"
                "        endif()\n"
                "        if(TARGET Qt5::${_comp})\n"
                "            set(Qt5_${_comp}_FOUND TRUE)\n"
                "        endif()\n"
                "    endif()\n"
                "endforeach()\n"
                "foreach(_comp ${Qt5_FIND_COMPONENTS})\n"
                "    if(NOT Qt5_${_comp}_FOUND AND NOT TARGET Qt5::${_comp})\n"
                "        set(Qt5_FOUND FALSE)\n"
                "        if(Qt5_FIND_REQUIRED_${_comp})\n"
                '            message(FATAL_ERROR "Qt5 component ${_comp} unresolved (test bridge)")\n'
                "        endif()\n"
                "    endif()\n"
                "endforeach()\n"
            )

    def _stage_fixed_qtbase_cmake(self):
        """Same fix as the kirigami2 recipe: stage a relocatable copy of
        the qt5-qtbase CMake config tree whose
        Qt5CoreConfigExtrasMkspecDir.cmake carries a build-tree remnant
        (``${prefix}/../b//mkspecs/linux-clang``)."""
        qtbase = self.dependencies["qt5-qtbase"]
        src = os.path.join(qtbase.package_folder, "lib", "cmake")
        marker = os.path.join(src, "Qt5Core", "Qt5CoreConfigExtrasMkspecDir.cmake")
        if not os.path.isfile(marker):
            return
        with open(marker, "r", encoding="utf-8") as f:
            content = f.read()
        if "/../b/" not in content:
            return
        staged_root = os.path.join(self.generators_folder, "qt5base-cmake-fixed")
        staged_cmake = os.path.join(staged_root, "lib", "cmake")
        if os.path.isdir(staged_cmake):
            shutil.rmtree(staged_cmake)
        shutil.copytree(src, staged_cmake)
        for entry in os.listdir(qtbase.package_folder):
            src_entry = os.path.join(qtbase.package_folder, entry)
            if entry == "lib":
                staged_lib = os.path.join(staged_root, "lib")
                os.makedirs(staged_lib, exist_ok=True)
                for lib_entry in os.listdir(src_entry):
                    if lib_entry == "cmake":
                        continue
                    dst_link = os.path.join(staged_lib, lib_entry)
                    if not os.path.lexists(dst_link):
                        os.symlink(os.path.join(src_entry, lib_entry), dst_link)
                continue
            dst_link = os.path.join(staged_root, entry)
            if not os.path.lexists(dst_link):
                os.symlink(src_entry, dst_link)
        staged_marker = os.path.join(staged_cmake, "Qt5Core", "Qt5CoreConfigExtrasMkspecDir.cmake")
        fixed = re.sub(
            r"\$\{_qt5Core_install_prefix\}/\.\./b//mkspecs/linux-clang",
            "${_qt5Core_install_prefix}/mkspecs/linux-clang",
            content,
        )
        with open(staged_marker, "w", encoding="utf-8") as f:
            f.write(fixed)

    def _write_cmake_paths(self):
        """Same path seeding strategy as the kirigami2 recipe: gather every
        dependency prefix (CMakeDeps-generated + native config trees) so
        find_package(Qt5 ...) resolves the per-component configs across
        the Conan qt5-* package split. The staged fixed qtbase tree is
        prepended so its mkspec fix wins over the published copy."""
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(self.dependencies.test.values()):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))
                add_unique(modules, os.path.join(dep.package_folder, "lib", "cmake"))

        staged = os.path.join(self.generators_folder, "qt5base-cmake-fixed")
        ordered = []
        if os.path.isdir(staged):
            ordered.append(staged)
        ordered.extend(prefixes)

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(ordered)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._prepare_runtime_links()
        self._dump_test_dynamic_section()

        env = Environment()
        deps = list(self.dependencies.values()) + list(self.dependencies.test.values())
        kirigami2 = self.dependencies["kirigami2"]
        qml_root = os.path.join(kirigami2.package_folder, "lib", "qml")

        env.define("KIRIGAMI2_PKG_DIR", kirigami2.package_folder)
        env.define("KIRIGAMI2_QML_DIR", qml_root)

        # Qt5 QML import paths: every dependency package ships its QML
        # modules below <pkg>/qml (the Qt5 conan layout).
        extra_qml_paths = []
        for dep_name in _QML_DEPENDENCIES + ("kirigami2",):
            dep = None
            for candidate in (self.dependencies.values(), self.dependencies.test.values()):
                for d in candidate:
                    if d.ref.name == dep_name:
                        dep = d
                        break
            if dep and dep.package_folder:
                for sub in ("qml", os.path.join("lib", "qml")):
                    qml_path = os.path.join(dep.package_folder, sub)
                    if os.path.isdir(qml_path):
                        env.prepend_path("QML2_IMPORT_PATH", qml_path)
                        extra_qml_paths.append(qml_path)

        env.define("KIRIGAMI2_QML_EXTRA_PATHS", os.pathsep.join(extra_qml_paths))

        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))

        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("QV4_FORCE_INTERPRETER", "1")
        env.define("QML_DISABLE_DISK_CACHE", "1")

        library_paths = [
            os.path.join(dep.package_folder, "lib")
            for dep in deps
            if dep and dep.package_folder
        ]
        runtime_prefix = "LD_LIBRARY_PATH={} QT_QPA_PLATFORM=offscreen".format(
            shlex.quote(os.pathsep.join(library_paths))
        )
        with env.vars(self).apply():
            self.run(
                '{} ctest --test-dir {} --output-on-failure --no-tests=error'.format(
                    runtime_prefix, shlex.quote(self.build_folder)
                ),
                env="",
            )
            self.run(
                "{} {}".format(
                    runtime_prefix,
                    shlex.quote(os.path.join(self.cpp.build.bindirs[0], "test_kirigami2")),
                ),
                env="",
            )
            self.run(
                "{} {}".format(
                    runtime_prefix,
                    shlex.quote(os.path.join(self.cpp.build.bindirs[0], "test_kirigami2_harmonyos")),
                ),
                env="",
            )

    def _dump_test_dynamic_section(self):
        executable = os.path.join(self.cpp.build.bindirs[0], "test_kirigami2")
        self.output.info("OHOS test executable dynamic section:")
        self.run("llvm-readelf -d {}".format(shlex.quote(executable)), ignore_errors=True)

    def _prepare_runtime_links(self):
        """Copy the runtime shared libraries next to the test executables.

        The OHOS loader resolves the sibling-relative DT_NEEDED entries of
        the Qt5/QML libraries against the working directory, so stage
        every dependency .so next to the built test binaries. Only the
        test build directory is written — never the dependency package
        folders (they must stay pristine)."""
        runtime_dirs = {self.cpp.build.bindirs[0], self.build_folder}
        lib_sources = []
        deps = list(self.dependencies.values()) + list(self.dependencies.test.values())
        for dep in deps:
            if dep and dep.package_folder:
                lib_sources.extend(glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*")))
        for src in lib_sources:
            for runtime_dir in runtime_dirs:
                os.makedirs(runtime_dir, exist_ok=True)
                dst = os.path.join(runtime_dir, os.path.basename(src))
                if os.path.exists(dst) or os.path.abspath(src) == os.path.abspath(dst):
                    continue
                shutil.copy2(src, dst)
