#!/usr/bin/env python3
"""Conan test_package for kio 6.14.0.

Verifies that kio's own KF6KIOConfig.cmake (the package is consumed with
cmake_find_mode=none) can be found with its full KF6 dependency closure and
that the libKF6KIOCore API is callable (R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{qt_pkg}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")'
            )
        # KF6KIOConfig.cmake runs find_dependency() on every KF6 dependency,
        # so every dependency's lib/cmake dir must be on CMAKE_PREFIX_PATH.
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
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

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Temporary platform cache-root bridge. The release machines built and
        # published the dependency packages (kservice, kcrash, kauth, ...) with
        # the conan cache rooted at ~/.conan2, so their .so files carry
        # absolute DT_NEEDED entries such as
        #   /storage/Users/currentUser/.conan2/p/<phash>/p/lib/libKF6*.so
        # The PR-check workers keep the same cache under ~/.cache/conan2 and
        # musl performs no fallback for slash-qualified NEEDED entries, so the
        # loader fails unless every baked path also exists locally. Until the
        # SONAME full-family fix for the published dependencies lands (the
        # 0015 pattern generalized to the KF6 family), recreate each baked
        # prefix as a symlink to the real package folder. This does not touch
        # the test oracle; it only makes the already-published absolute-path
        # NEEDED entries resolvable on machines whose conan root differs.
        # Remove once the rebuilt dependency packages ship.
        bridges = []
        for dep in self.dependencies.values():
            try:
                folder = dep.package_folder if dep else None
                if not folder:
                    continue
                idx = folder.rfind("/p/")
                if idx < 0:
                    continue
                # Suffix exactly as baked into DT_NEEDED, e.g. "p/<phash>/p".
                rest = folder[idx + 1:]
                legacy = os.path.expanduser("~/.conan2") + "/" + rest
                if os.path.abspath(legacy) == os.path.abspath(folder):
                    continue
                if os.path.lexists(legacy):
                    continue
                os.makedirs(os.path.dirname(legacy), exist_ok=True)
                os.symlink(folder, legacy)
                bridges.append(legacy)
            except Exception as exc:  # bridge is best-effort, never fatal
                self.output.warning(
                    f"cache-root bridge skipped for "
                    f"{getattr(dep, 'name', 'dependency')}: {exc}"
                )
        if bridges:
            self.output.info(
                "cache-root bridges created: " + ", ".join(bridges)
            )
        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        # Headless sandbox: offscreen QPA plus a writable HOME/XDG runtime so
        # the KSycoca lookup in KProtocolInfo cannot touch a real session.
        env.define("QT_QPA_PLATFORM", "offscreen")
        # Let ctest print the failing tests' output directly into the build log.
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kio"),
                env="conanrun",
            )
