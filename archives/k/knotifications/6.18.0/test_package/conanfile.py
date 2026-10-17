#!/usr/bin/env python3
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import save


class KnotificationsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.18.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        library_paths = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep and dep.package_folder
        ]
        tc = CMakeToolchain(self)
        # The OHOS loader ignores LD_LIBRARY_PATH for this signed test ELF.
        # Embed dependency paths as DT_RPATH so the consumer can load the
        # package it was linked against without relying on process state.
        tc.variables["CMAKE_BUILD_RPATH"] = ";".join(library_paths)
        tc.variables["CONAN_RUNTIME_LIB_DIRS"] = ";".join(library_paths)
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags,-rpath,{}".format(
            os.pathsep.join(library_paths)
        )
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_runtime_rules(tc)
        tc.generate()
        self._write_cmake_paths()

    def _configure_ohos_runtime_rules(self, toolchain):
        rules = os.path.join(self.generators_folder, "ohos-runtime-rules.cmake")
        save(
            self,
            rules,
            "\n".join((
                'set(CMAKE_EXECUTABLE_RUNTIME_C_FLAG "-Wl,-rpath,")',
                'set(CMAKE_EXECUTABLE_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                'set(CMAKE_EXECUTABLE_RUNTIME_C_FLAG_SEP ":")',
                'set(CMAKE_EXECUTABLE_RUNTIME_CXX_FLAG_SEP ":")',
            )) + "\n",
        )
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

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
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        library_paths = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep and dep.package_folder
        ]
        runtime_prefix = "LD_LIBRARY_PATH={} QT_QPA_PLATFORM=offscreen".format(
            shlex.quote(os.pathsep.join(library_paths))
        )
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_knotifications")
        tested_library = os.path.join(
            self.dependencies["knotifications"].package_folder,
            "lib",
            "libKF6Notifications.so",
        )
        with env.vars(self).apply():
            # Record ELF loader metadata before execution; this distinguishes a
            # missing RPATH from an OHOS loader staging-policy rejection.
            for elf in (test_binary, tested_library):
                if not os.path.isfile(elf):
                    self.output.info("Static package has no shared-library ELF: {}".format(elf))
                    continue
                self.run(
                    "if command -v llvm-readelf >/dev/null 2>&1; then "
                    "llvm-readelf -d {0}; "
                    "elif command -v readelf >/dev/null 2>&1; then "
                    "readelf -d {0}; "
                    "else echo 'ELF dynamic-section tool unavailable'; fi".format(
                        shlex.quote(elf)
                    ),
                    env="",
                )
            self.run(
                '{} ctest --test-dir {} --output-on-failure --no-tests=error'.format(
                    runtime_prefix, shlex.quote(self.build_folder)
                ), env="",
            )
            self.run(
                '{} {}'.format(runtime_prefix, shlex.quote(os.path.join(self.cpp.build.bindirs[0], "test_knotifications"))), env="",
            )
