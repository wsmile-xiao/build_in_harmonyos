import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
)


class AbseilConan(ConanFile):
    name = "abseil"
    version = "20260526"
    description = "Abseil Common Libraries (C++) from Google"
    license = "Apache-2.0"
    homepage = "https://abseil.io"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        candidates = []
        if cxx:
            compiler = os.path.realpath(cxx)
            try:
                resource_dir = subprocess.check_output(
                    [cxx, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )

        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def _usable_sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""

        cached = getattr(self, "_checked_sdk_llvm_libdir", None)
        if cached is not None:
            return cached

        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            lld = os.path.join(os.path.dirname(sdk_llvm_lib), "bin", "lld")
            probe_env = os.environ.copy()
            old_ld_path = probe_env.get("LD_LIBRARY_PATH", "")
            probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (sdk_llvm_lib, old_ld_path) if part
            )
            try:
                probe = subprocess.run(
                    [lld, "-flavor", "gnu", "--version"],
                    env=probe_env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as error:
                raise ConanException(
                    f"Cannot execute the active OHOS SDK linker {lld}: {error}"
                ) from error
            if probe is not None and probe.returncode == 0:
                self._checked_sdk_llvm_libdir = sdk_llvm_lib
                return sdk_llvm_lib
            raise ConanException(
                f"The active OHOS SDK linker failed its GNU-flavor probe: {lld}; "
                f"stderr={probe.stderr.strip()!r}"
            )

        raise ConanException(
            "Cannot locate the active OHOS SDK llvm/lib containing "
            "libxml2.so.16"
        )

    def _build_environment(self):
        environment = Environment()
        sdk_llvm_lib = self._usable_sdk_llvm_libdir()
        if sdk_llvm_lib:
            # CI shells prepend ~/usr/local/lib, which can shadow the SDK's
            # ABI-matched libxml2.so.16 and prevent lld from starting.
            self.output.info(
                f"Prepending OHOS SDK linker runtime path: {sdk_llvm_lib}"
            )
            environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return environment

    def build_requirements(self):
        self.test_requires("gtest/1.17.0")

    def generate(self):
        toolchain = CMakeToolchain(self)
        gtest = self.dependencies["gtest"]
        toolchain.variables["ABSL_ENABLE_INSTALL"] = True
        toolchain.variables["ABSL_PROPAGATE_CXX_STD"] = True
        toolchain.variables["ABSL_BUILD_TESTING"] = True
        toolchain.variables["ABSL_BUILD_TEST_HELPERS"] = False
        toolchain.variables["ABSL_USE_EXTERNAL_GOOGLETEST"] = True
        toolchain.variables["ABSL_FIND_GOOGLETEST"] = True
        toolchain.variables["BUILD_TESTING"] = True
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["CMAKE_CXX_STANDARD"] = 17
        toolchain.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        toolchain.variables["GTest_DIR"] = os.path.join(
            gtest.package_folder, "lib", "cmake", "GTest"
        ).replace("\\", "/")
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build()
        if can_run(self):
            test_env = Environment()
            test_env.define_path(
                "TZDIR",
                os.path.join(
                    self.source_folder,
                    "absl",
                    "time",
                    "internal",
                    "cctz",
                    "testdata",
                    "zoneinfo",
                ),
            )
            if str(self.settings.os) == "OHOS":
                test_env.define(
                    "GTEST_FILTER",
                    "-FromChars.NaNDoubles:FromChars.NaNFloats",
                )
            test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
            with test_env.vars(self).apply():
                cmake.test()

    def package(self):
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            # Regenerate install/export rules without test helpers or GTest targets.
            cmake.configure(
                variables={
                    "ABSL_BUILD_TESTING": False,
                    "BUILD_TESTING": False,
                }
            )
            cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Preserve the component-rich abslConfig.cmake and its absl::* targets.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs.append(os.path.join("lib", "cmake", "absl"))
        self.cpp_info.libs = sorted(collect_libs(self))
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
