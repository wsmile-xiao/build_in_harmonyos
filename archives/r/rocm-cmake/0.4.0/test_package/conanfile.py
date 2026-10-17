import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class RocmCMakeTestConan(ConanFile):
    """Consumer-side test for rocm-cmake.

    Builds a program that includes the package's CMake modules, asserts the
    macro-level version contract at configure time, and installs/exports a real
    library, then runs the produced binary for a runtime re-check.
    """
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _consumer_env(self):
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        rocm_dir = os.path.join(pkg_folder, "share", "rocm", "cmake")
        env = Environment()
        # ROCM_DIR lets the consumer CMakeLists locate ROCMConfig.cmake, and
        # doubles as the CMAKE_MODULE_PATH entry for the individual modules.
        env.define("ROCM_DIR", rocm_dir)
        # rocm_get_patch_version() reads ROCM_LIBPATCH_VERSION from the
        # environment; the consumer CMakeLists asserts it equals "0".
        env.define("ROCM_LIBPATCH_VERSION", "0")
        return env

    def build(self):
        # Pass ROCM_DIR / ROCM_LIBPATCH_VERSION through Conan's Environment API
        # (no bare shell variables, R33) so the configure step can find the
        # package and read the patch version.
        env = self._consumer_env()
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
            # Install so the install(CODE ...) assertions in CMakeLists.txt
            # (verifying rocm_install_targets / rocm_export_targets real output)
            # actually execute instead of being silently skipped.
            cmake.install()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: consumer binary built but not run")
            return
        env = Environment()
        if str(self.settings.os) == "OHOS":
            # On OHOS the musl loader stops resolving LD_LIBRARY_PATH entries
            # after the huge app-bundle directory; prepend the system lib dir
            # so libc++_shared.so resolves (see DRAFT-13536-libzmq-*-ohos-ldso).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_package"),
                     env="conanrun")
