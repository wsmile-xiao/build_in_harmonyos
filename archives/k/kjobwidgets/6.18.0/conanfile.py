#!/usr/bin/env python3
"""Conan recipe for kjobwidgets 6.18.0 on HarmonyOS PC."""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class KjobwidgetsConan(ConanFile):
    name = "kjobwidgets"
    version = "6.18.0"
    description = "KDE Frameworks 6 - widget helpers for KJob"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kjobwidgets"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("knotifications/6.18.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase_dbus = self.dependencies.host.get("qtbase-sql-dbus")
        if qtbase_dbus and qtbase_dbus.package_folder:
            tc.variables["Qt6_DIR"] = os.path.join(qtbase_dbus.package_folder, "lib", "cmake", "Qt6")
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["BUILD_PYTHON_BINDINGS"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["USE_DBUS"] = "ON"
        tc.variables["WITH_X11"] = "OFF"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)
        self._define_ecm(tc)
        self._write_cmake_paths()
        tc.generate()

    def _configure_ohos_shared_library_rules(self, tc):
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(self, rules, "\n".join((
            'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
            'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
            'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
            'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
            'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
            'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
        )) + "\n")
        tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

    def _define_ecm(self, tc):
        ecm = self.dependencies.build.get("ecm")
        if not ecm:
            return
        ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
        tc.variables["ECM_MODULE_PATH"] = ";".join(
            os.path.join(ecm_share, rel)
            for rel in ("modules", "find-modules", "kde-modules")
        )

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")',
                    ]
                )
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        test_env = Environment()
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        with test_env.vars(self).apply():
            self.run(
                "ctest --output-on-failure -R '^(kjobtrackerstest|kjobcreator|kuiserver2jobtrackertest)$'",
                cwd=self.build_folder,
            )

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_ohos_elf_tree(self, root_folder):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanException("Cannot locate OHOS binary-sign-tool")
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if not os.path.islink(path) and self._is_elf(path):
                    self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')

    def _normalize_ohos_needed_names(self):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        pattern = re.compile(rb"(?:/[^/\x00]+)+/(lib[^/\x00]+)")
        for root, _, files in os.walk(os.path.join(self.package_folder, "lib")):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                with open(path, "rb") as handle:
                    data = handle.read()

                def replace(match):
                    value = match.group(1)
                    return value + b"\x00" * (len(match.group(0)) - len(value))

                updated, count = pattern.subn(replace, data)
                if count:
                    with open(path, "wb") as handle:
                        handle.write(updated)

    def package(self):
        CMake(self).install()
        self._normalize_ohos_needed_names()
        self._sign_ohos_elf_tree(self.package_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6JobWidgets"]
