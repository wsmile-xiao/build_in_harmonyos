#!/usr/bin/env python3
"""Consumer test for libodsstream 0.9.18.

Writes an ODS file through OdsDocWriter (the library's main API: sheets,
cells of several types, cell styles/color scales), reads it back through
OdsDocReader with a custom handler, and asserts the round-trip content.
Also exercises the TSV writer path. This is the consumer-side validation
complementing the 5 upstream Catch2 TEST_CASEs (test_ods 2 + test_tsv 2 +
test_zlib 1) that run during conan create.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class LibodsstreamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # OdsStreamConfig.cmake (installed with the package) declares
        # find_dependency names Qt6/Qt6Core5Compat/zlib. qtbase and
        # qt5compat use cmake_find_mode=none (their own upstream configs
        # under lib/cmake), so wire their package dirs into
        # CMAKE_PREFIX_PATH through conan_cmakedeps_paths.cmake, and map
        # zlib through CMakeDeps.
        import os
        from conan.tools.cmake import CMakeDeps
        deps = CMakeDeps(self)
        # libodsstream ships its own OdsStreamConfig.cmake (upstream
        # install(EXPORT)) — use it, not a CMakeDeps-generated one.
        deps.set_property("libodsstream", "cmake_find_mode", "none")
        deps.generate()
        lines = []
        # libodsstream ships the vendored QuaZip-Qt6 config under
        # lib/cmake/QuaZip-Qt6 — put it on the prefix path.
        tested = self.dependencies.get("libodsstream")
        if tested:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{tested.package_folder}/lib/cmake")'
            )
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        qt5compat = self.dependencies.get("qt5compat")
        if qt5compat:
            q5 = qt5compat.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{q5}/lib/cmake")')
            # Qt6 component lookup (find_package(Qt6 COMPONENTS Core5Compat))
            # only scans _qt_cmake_dir + QT_ADDITIONAL_PACKAGES_PREFIX_PATH —
            # point it at qt5compat's official Qt6Core5Compat config so the
            # component resolves (phonon precedent).
            lines.append(
                f'set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH "{q5}/lib/cmake")'
            )
        lines.insert(0, f'list(PREPEND CMAKE_PREFIX_PATH "{self.generators_folder}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        from conan.tools.env import Environment
        # conanrun lacks the OHOS SDK libc++ dir on this host; prepend the
        # dependency lib dirs (incl. /system/lib64 for libc++_shared.so).
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(dep.package_folder, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            cmd = os.path.join(self.cpp.build.bindirs[0], "test_odsstream")
            self.run(f"{cmd}", env="conanrun")
