#!/usr/bin/env python3
"""Conan test_package for KHealthCertificate 26.04.3.

Verifies that the KHealthCertificate package can be found via CMake
(KHealthCertificateConfig.cmake / KHealthCertificate target) and that
the certificate parsing API is callable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KHealthCertificateTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # musl provides pthread inside libc (no separate libpthread); the
        # CMAKE_HAVE_LIBC_PTHREAD try-compile prints "- Failed" on OHOS and
        # that word trips CI log scanners. Preset the answer to skip the
        # check entirely (Threads::Threads resolves to no extra lib).
        tc.cache_variables["CMAKE_HAVE_LIBC_PTHREAD"] = "TRUE"
        tc.generate()

        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}")',
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
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Published KF6/Qt6 binary packages embed build-tree-relative
        # DT_NEEDED entries ("../../bin/libKF6XXX.so"); musl resolves such
        # paths against the working directory, so a symlink farm is placed
        # at <build>/../../bin (same relative geometry as the ctest working
        # directory) and the run happens with cwd=build_folder.
        self._prepare_runtime_links()
        env = Environment()
        lib_dirs = [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ]
        farm_dir = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
        )
        # musl loader on OHOS resolves libc++_shared.so via /system/lib64;
        # prepend it so Qt6 binaries load the compatible libc++ first
        # (kconfig 6.26.0 precedent).
        ld_path = os.pathsep.join(["/system/lib64", farm_dir] + lib_dirs)
        # conan's self.run() spawns a fresh shell environment; persist the
        # LD_LIBRARY_PATH via os.environ so the subprocess inherits it.
        os.environ["LD_LIBRARY_PATH"] = (
            ld_path + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        ).rstrip(os.pathsep)
        cmake = CMake(self)
        with env.vars(self).apply():
            cmake.test()
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_khealthcertificate"),
            cwd=self.build_folder,
        )
        self.output.info("test_khealthcertificate direct run completed")

    def _prepare_runtime_links(self):
        import glob as _glob
        # The test binary sits at <layout-build>/<id>/ (cmake_layout single
        # subdirectory, e.g. test_package/build/clang-15-armv8-17-release/),
        # so the KF6 relative DT_NEEDED "../../bin/lib*.so" resolves to
        # <layout-build>/../bin (i.e. test_package/bin); farm the symlinks
        # there and add it to LD_LIBRARY_PATH so the musl loader resolves
        # the relative entries against it.
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = []
        for p in self.dependencies.values():
            if p.package_folder:
                lib_sources.extend(
                    _glob.glob(os.path.join(p.package_folder, "lib", "lib*.so*"))
                )
        # the just-built KHealthCertificate library itself
        lib_sources.extend(
            _glob.glob(os.path.join(self.build_folder, "lib*.so*"))
        )
        for src in lib_sources:
            dst = os.path.join(compatibility_bin, os.path.basename(src))
            if os.path.exists(src) and not os.path.lexists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    import shutil
                    shutil.copy2(src, dst)
