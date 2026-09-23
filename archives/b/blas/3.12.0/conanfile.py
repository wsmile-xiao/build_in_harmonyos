"""Conan recipe for the Netlib reference BLAS 3.12.0 on HarmonyOS PC."""

import glob
import os
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class BlasConan(ConanFile):
    name = "blas"
    version = "3.12.0"
    description = "Reference implementation of the Basic Linear Algebra Subprograms"
    license = "BSD-3-Clause"
    homepage = "https://www.netlib.org/blas/"
    url = ""
    exports = "LICENSE"

    package_type = "static-library"
    no_copy_source = True
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    _source_url = "https://www.netlib.org/blas/blas-3.12.0.tgz"
    _source_sha256 = "ccc41b5d088e50db0030317ae9b0c9af375710c1392acad1fe209602da5a5aad"

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "blas/3.12.0 supports OHOS armv8 only"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "blas/3.12.0 is packaged as a static library on OHOS"
            )

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        cmake_layout(self)
        self.folders.source = "."

    def source(self):
        get(
            self,
            url=self._source_url,
            sha256=self._source_sha256,
            strip_root=False,
        )

    def _flang_package(self):
        package = self.dependencies.build.get("flang-ohos")
        if not package:
            raise ConanException("flang-ohos/20.1.0 tool requirement is missing")
        return package.package_folder

    def _sdk_paths(self):
        llvm_roots = sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm")
        )
        if not llvm_roots:
            raise ConanException("OHOS SDK LLVM root was not found")
        llvm_root = llvm_roots[-1]
        return {
            "llvm": llvm_root,
            "sysroot": os.path.normpath(os.path.join(llvm_root, "..", "sysroot")),
            "resource": os.path.join(llvm_root, "lib", "clang", "15.0.4"),
            "target_lib": os.path.join(llvm_root, "lib", "aarch64-linux-ohos"),
        }

    def _set_build_environment(self):
        flang_package = self._flang_package()
        sdk_paths = self._sdk_paths()
        sdk_llvm_lib = os.path.join(sdk_paths["llvm"], "lib")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [sdk_llvm_lib, os.path.join(flang_package, "lib")]
        )
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        for variable in (
            "CFLAGS",
            "CXXFLAGS",
            "CPPFLAGS",
            "LDFLAGS",
            "CMAKE_PREFIX_PATH",
            "PKG_CONFIG_PATH",
        ):
            os.environ.pop(variable, None)

    def generate(self):
        flang_package = self._flang_package()
        sdk_paths = self._sdk_paths()
        flang = os.path.join(flang_package, "bin", "flang")
        runtime = os.path.join(flang_package, "lib", "libFortranRuntime.a")
        decimal = os.path.join(flang_package, "lib", "libFortranDecimal.a")

        for required in (flang, runtime, decimal):
            if not os.path.isfile(required):
                raise ConanException("required flang input is missing: {}".format(required))

        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        tc.cache_variables["BUILD_SHARED_LIBS"] = False
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["LAPACK_VERSION"] = self.version
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.cache_variables["CMAKE_Fortran_COMPILER"] = flang
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.cache_variables["CMAKE_Fortran_FLAGS"] = (
            "-fPIC --target=aarch64-linux-ohos "
            "--sysroot={} -resource-dir={}".format(
                sdk_paths["sysroot"], sdk_paths["resource"]
            )
        )
        tc.cache_variables["CMAKE_Fortran_LINK_FLAGS"] = (
            "-L{} -L{} {} {} -lm".format(
                sdk_paths["target_lib"],
                os.path.join(flang_package, "lib"),
                runtime,
                decimal,
            )
        )
        tc.generate()

    def build(self):
        self._set_build_environment()
        cmake = CMake(self)
        cmake.configure(build_script_folder="BLAS-3.12.0")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        copy(
            self,
            "LICENSE",
            src=self.recipe_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

        flang_package = self._flang_package()
        for runtime_name in ("libFortranRuntime.a", "libFortranDecimal.a"):
            runtime = os.path.join(flang_package, "lib", runtime_name)
            if not os.path.isfile(runtime):
                raise ConanException("Fortran runtime is missing: {}".format(runtime))
            copy(
                self,
                runtime_name,
                src=os.path.dirname(runtime),
                dst=os.path.join(self.package_folder, "lib"),
            )

    def package_info(self):
        self.cpp_info.libs = ["blas", "FortranRuntime", "FortranDecimal"]
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "blas")
        self.cpp_info.set_property("cmake_target_name", "blas::blas")
        self.cpp_info.set_property("pkg_config_name", "blas")
        self.cpp_info.system_libs = ["m"]
