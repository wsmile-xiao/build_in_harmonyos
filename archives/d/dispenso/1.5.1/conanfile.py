import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class DispensoConan(ConanFile):
    name = "dispenso"
    version = "1.5.1"
    description = "A modern C++ library for parallel tasks"
    license = "MIT"
    homepage = "https://github.com/facebookincubator/dispenso"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build_requirements(self):
        self.test_requires("gtest/1.17.0")

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["DISPENSO_SHARED_LIB"] = bool(self.options.shared)
        toolchain.variables["DISPENSO_BUILD_TESTS"] = True
        toolchain.variables["DISPENSO_BUILD_BENCHMARKS"] = False
        toolchain.variables["DISPENSO_BUILD_EXAMPLES"] = False
        toolchain.variables["DISPENSO_BUILD_FAST_MATH"] = False
        toolchain.variables["DISPENSO_USE_SYSTEM_CONCURRENTQUEUE"] = False
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe(
            "fPIC", True
        )
        gtest = self.dependencies["gtest"]
        toolchain.variables["GTest_DIR"] = os.path.join(
            gtest.package_folder, "lib", "cmake", "GTest"
        ).replace("\\", "/")
        if self.settings.os == "OHOS":
            # The OHOS SDK injects --gcc-toolchain even though its Clang driver
            # does not consume it. Dispenso otherwise promotes every warning to
            # an error, so demote this one driver diagnostic only.
            # A cache entry is required because the SDK toolchain rewrites the
            # initial flag variables after Conan's regular extra flags run.
            toolchain.cache_variables["CMAKE_CXX_FLAGS"] = (
                "-Wno-error=unused-command-line-argument"
            )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            command = [
                "ctest",
                "--output-on-failure",
                "--no-tests=error",
                "--label-exclude",
                "flaky",
                "--parallel",
                "4",
            ]
            result = subprocess.run(
                command,
                cwd=self.build_folder,
                capture_output=True,
                text=True,
                timeout=1800,
                check=False,
            )
            output = (result.stdout or "") + (result.stderr or "")
            summary = re.search(
                r"(\d+)% tests passed, (\d+) tests failed out of (\d+)",
                output,
            )
            total = int(summary.group(3)) if summary else 0
            failed = int(summary.group(2)) if summary else total
            passed = total - failed
            print("\n".join(output.splitlines()[-12:]), flush=True)
            marker = {
                "status": (
                    "passed"
                    if result.returncode == 0 and total == 1080 and failed == 0
                    else "failed"
                ),
                "framework": "gtest/ctest",
                "command": " ".join(command),
                "discovered": total,
                "executed": total,
                "passed": passed,
                "failed": failed,
                "skipped": 0,
                "note": "Upstream's official automated suite excludes the flaky label",
            }
            print(
                "HMBS_UPSTREAM_TEST_RESULT="
                + json.dumps(marker, ensure_ascii=False),
                flush=True,
            )
            if marker["status"] != "passed":
                raise ConanException(
                    "Upstream stable CTest suite did not pass 1080/1080"
                )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["dispenso"]
        self.cpp_info.includedirs = [
            "include",
            os.path.join("include", "dispenso", "third-party"),
        ]
        self.cpp_info.set_property("cmake_file_name", "Dispenso")
        self.cpp_info.set_property("cmake_target_name", "Dispenso::dispenso")
        if self.options.shared:
            self.cpp_info.defines.append("DISPENSO_SHARED_LIB")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
