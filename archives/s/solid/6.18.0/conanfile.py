#!/usr/bin/env python3
"""Conan recipe for solid 6.18.0 on HarmonyOS PC."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class SolidConan(ConanFile):
    name = "solid"
    version = "6.18.0"
    description = "KDE Frameworks 6 - hardware integration library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/solid"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("m4/1.4.19")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["UDEV_DISABLED"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_IMobileDevice"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_PList"] = "ON"
        self._define_tool_executables(tc)
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)
        self._define_ecm(tc)
        self._write_cmake_paths()
        tc.generate()

    def _configure_ohos_shared_library_rules(self, tc):
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(
            self,
            rules,
            "\n".join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
            )) + "\n",
        )
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

    def _define_tool_executables(self, tc):
        tool_map = {
            "bison": "BISON_EXECUTABLE",
            "flex": "FLEX_EXECUTABLE",
        }
        for dep_name, variable in tool_map.items():
            dep = self.dependencies.build.get(dep_name)
            if dep and dep.package_folder:
                tc.variables[variable] = os.path.join(dep.package_folder, "bin", dep_name)

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if not dep or not dep.package_folder:
                continue
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
        with self._tool_environment().vars(self).apply():
            cmake.configure()
            cmake.build()

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        found = shutil.which(name)
        if found:
            return found
        return os.path.join("/data/service/hnp/bin", name)

    def _sign_ohos_elf_tree(self, root_folder):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        signer = self._find_ohos_tool("binary-sign-tool")
        if not os.path.isfile(signer):
            raise ConanException("Cannot locate OHOS binary-sign-tool")
        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package(self):
        CMake(self).install()
        self._sign_ohos_elf_tree(self.package_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Solid"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))

    def _tool_environment(self):
        env = Environment()
        for dep_name in ("bison", "flex", "m4"):
            dep = self.dependencies.build.get(dep_name)
            if dep and dep.package_folder:
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        bison = self.dependencies.build.get("bison")
        if bison and bison.package_folder:
            env.define(
                "BISON_PKGDATADIR",
                os.path.join(bison.package_folder, "share", "bison"),
            )
        m4 = self.dependencies.build.get("m4")
        if m4 and m4.package_folder:
            env.define("M4", os.path.join(m4.package_folder, "bin", "m4"))
        return env
