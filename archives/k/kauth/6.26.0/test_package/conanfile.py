#!/usr/bin/env python3
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KauthTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kcoreaddons/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        library_paths = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep and dep.package_folder
        ]
        tc = CMakeToolchain(self)
        tc.variables["CONAN_RUNTIME_LIB_DIRS"] = ";".join(library_paths)
        tc.variables["CMAKE_BUILD_RPATH"] = ";".join(library_paths)
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
            "-Wl,--disable-new-dtags,-rpath," + os.pathsep.join(library_paths)
        )
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")',
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
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        library_paths = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep and dep.package_folder
        ]
        # kauth is packaged as a static library (shared=False), so there is no
        # libKF6AuthCore.so.6 to LD_PRELOAD. Only the dependency search path is
        # needed: on OHOS the loader does not honour the consumer RPATH here, so
        # pass the Conan dependency directories in the command environment
        # explicitly.
        runtime_prefix = "LD_LIBRARY_PATH={}".format(
            shlex.quote(os.pathsep.join(library_paths)),
        )
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_kauth")
        self.run(
            "if command -v llvm-readelf >/dev/null 2>&1; then "
            "llvm-readelf -d {0}; "
            "elif command -v readelf >/dev/null 2>&1; then "
            "readelf -d {0}; "
            "else echo 'ELF dynamic-section tool unavailable'; fi".format(
                shlex.quote(test_binary)
            ),
            env="",
        )
        self.run(
            "{} {}".format(runtime_prefix, shlex.quote(test_binary)),
            env="",
        )

        # HarmonyOS-specific test (rule12), runtime half: assert the observable
        # behavior of the OHOS FAKE-backend adaptation path (status() ==
        # DeniedStatus, execute() fails with BackendError, no helper bound).
        ohos_binary = os.path.join(self.cpp.build.bindirs[0], "test_kauth_ohos")
        self.run(
            "{} {}".format(runtime_prefix, shlex.quote(ohos_binary)),
            env="",
        )

        # HarmonyOS-specific test (rule12), artifact half: verify the packaged
        # libKF6AuthCore.a is a valid OHOS/aarch64 relocatable archive and that
        # no backend plugin is shipped (the FakeBackend fallback precondition).
        kauth_package_folder = self.dependencies["kauth"].package_folder
        self.run(
            "{} {} {}".format(
                shlex.quote(sys.executable),
                shlex.quote(os.path.join(self.source_folder, "fixtures", "ohos_artifact_check.py")),
                shlex.quote(kauth_package_folder),
            ),
            env="",
        )
