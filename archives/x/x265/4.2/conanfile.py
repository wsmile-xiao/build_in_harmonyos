import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class X265Conan(ConanFile):
    name = "x265"
    version = "4.2"
    description = "x265 is an open source HEVC (H.265) encoder"
    license = "GPL-2.0-only"
    homepage = "https://bitbucket.org/multicoreware/x265_git"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Skip the linking step in CMake try_compile (compiler detection).
        # On CI the lld linker from the OHOS SDK fails to load
        # libxml2.so.16 (its runtime dependency), causing try_compile to
        # fail before the real build even starts.  STATIC_LIBRARY avoids
        # invoking the linker during compiler identification, using
        # ar instead to create a static archive.
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        # Disable assembly — NASM/YASM is not available on OHOS CI workers.
        tc.variables["ENABLE_ASSEMBLY"] = "OFF"
        # Disable shared library and CLI builds.  The OHOS SDK lld linker
        # has a broken runtime dependency on libxml2.so.16 on certain CI
        # workers (CI-019), causing any linking step that invokes lld to
        # fail.  Since the package default is shared=False (static), we
        # skip the shared library (x265-shared) and CLI executable (cli)
        # targets entirely.  The static library (x265-static) uses ar,
        # not lld, so it is unaffected.
        tc.variables["ENABLE_SHARED"] = "OFF"
        tc.variables["ENABLE_CLI"] = "OFF"
        tc.generate()

        # Ensure lld (used by clang for linking) can locate its runtime
        # dependency libxml2.so.16.  The lld binary has RUNPATH
        # $ORIGIN/../lib, but on some CI workers the musl dynamic linker
        # does not resolve $ORIGIN in DT_RUNPATH, so we add the SDK lib
        # directory to LD_LIBRARY_PATH explicitly.
        env = Environment()
        lld_path = shutil.which("lld") or shutil.which("ld")
        if lld_path:
            lld_real = os.path.realpath(lld_path)
            sdk_lib = os.path.normpath(
                os.path.join(os.path.dirname(lld_real), "..", "lib")
            )
            if os.path.isdir(sdk_lib):
                env.append("LD_LIBRARY_PATH", sdk_lib)
        env.vars(self, scope="build").save_script("conan_lld_fix")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="source")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["x265"]
        # x265 is a C++ library; consumers linking the static archive
        # (e.g. the C-only test_package) need libc++ resolved at link time.
        self.cpp_info.system_libs = ["c++"]
        # Propagate LD_LIBRARY_PATH to consumers (test_package) so that
        # lld can find libxml2.so.16 during their build/test linking steps.
        lld_path = shutil.which("lld") or shutil.which("ld")
        if lld_path:
            lld_real = os.path.realpath(lld_path)
            sdk_lib = os.path.normpath(
                os.path.join(os.path.dirname(lld_real), "..", "lib")
            )
            if os.path.isdir(sdk_lib):
                self.buildenv_info.append("LD_LIBRARY_PATH", sdk_lib)
