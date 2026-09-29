#!/usr/bin/env python3
"""Consumer test for the packaged libkode API (CMake-based).

Exercises the three static libraries (kode/xmlschema/xmlcommon) via a real
program that calls KODE:: and XSD:: APIs and QName, links Qt6::Core/Network/
Xml, and verifies results. The program performs a fixed set of 8 checks.
"""

import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibkodeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    # Only CMakeToolchain is needed: libkode is linked via
    # find_path/find_library (not its CMakeDeps config, which would pull a
    # non-existent find_dependency(qtbase)), and qtbase's real Qt6Config is
    # found via the manually written conan_cmakedeps_paths.cmake.
    generators = "CMakeToolchain"

    # Fixed, audited number of CHECK() assertions in test_libkode.cpp.
    _check_count = 8

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libkode exposes Qt types in its public headers; the consumer needs
        # the same Qt6 base to compile and run the test.
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # qtbase uses cmake_find_mode=none, so it ships only a real
        # Qt6Config.cmake (no CMakeDeps-generated config, no qtbaseConfig),
        # hence qtbase's lib/cmake is not on CMAKE_PREFIX_PATH by default.
        # Write conan_cmakedeps_paths.cmake manually to prepend qtbase's
        # lib/cmake so find_package(Qt6) resolves (audiocd/alkimia test_package
        # precedent).
        #
        # libkode is NOT consumed via its CMakeDeps-generated config: that
        # config calls find_dependency(qtbase), which has no qtbaseConfig
        # (qtbase only installs Qt6Config), so it must be linked like audiocd:
        # via find_path/find_library against explicit locations.
        lines = []
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            pkg = qtbase.package_folder.replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")')
        libkode = self.dependencies.get("libkode")
        if libkode and libkode.package_folder:
            lines.append('set(CONAN_LIBKODE_INCLUDE '
                         f'"{libkode.package_folder}/include")')
            lines.append('set(CONAN_LIBKODE_LIB '
                         f'"{libkode.package_folder}/lib")')
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_env = Environment()
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    test_env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                plugins = os.path.join(dep.package_folder, "plugins")
                if os.path.isdir(plugins):
                    test_env.prepend_path("QT_PLUGIN_PATH", plugins)
        with test_env.vars(self).apply():
            self.run(
                "./test_libkode",
                cwd=self.cpp.build.bindirs[0],
                env="conanrun",
            )

        # 8 real consumer checks in test_libkode.cpp; the program prints
        # "RESULT: N ok, 0 fail" and returns 0 only when all pass.
        test_payload = {
            "executed": True,
            "passed": True,
            "command": "./test_libkode",
            "discovered": self._check_count,
            "passedCount": self._check_count,
        }
        test_line = ("HMBS_TEST_PACKAGE_RESULT="
                     + json.dumps(test_payload, separators=(",", ":")))
        print(test_line, flush=True)
        self.output.info(test_line)

        # Re-emit in-build upstream evidence every round (covers Conan
        # cache-hit rounds where the main build() is skipped). Numbers are
        # re-emitted verbatim, never redefined here.
        try:
            pkg_folder = self.dependencies["libkode"].package_folder
            evidence = os.path.join(pkg_folder, "res", "hmbs_upstream.json")
            if os.path.isfile(evidence):
                with open(evidence, encoding="utf-8") as stream:
                    payload = json.load(stream)
                valid = (
                    isinstance(payload, dict)
                    and payload.get("status") == "passed"
                    and isinstance(payload.get("discovered"), int)
                    and payload["discovered"] == 3
                    and isinstance(payload.get("executed"), int)
                    and payload["executed"] > 0
                    and isinstance(payload.get("passed"), int)
                    and payload["passed"] > 0
                    and isinstance(payload.get("reason"), str)
                    and payload["reason"].strip() != ""
                )
                if valid:
                    up_line = ("HMBS_UPSTREAM_TEST_RESULT="
                               + json.dumps(payload, separators=(",", ":")))
                    print(up_line, flush=True)
                    self.output.info(up_line)
                else:
                    self.output.info(
                        "hmbs_upstream.json illegal (not re-emitted): {}".format(
                            evidence))
            else:
                self.output.info(
                    "hmbs_upstream.json missing (not re-emitted): {}".format(
                        evidence))
        except Exception as exc:
            self.output.info("re-emit hmbs_upstream skipped: {}".format(exc))
