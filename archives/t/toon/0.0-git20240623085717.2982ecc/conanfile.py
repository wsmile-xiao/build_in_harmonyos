import os
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, check_sha256, copy,
                               export_conandata_patches, get, unzip)
from conan.tools.gnu import AutotoolsToolchain


CORE_TESTS = (
    "slice", "vector_resize", "gauss_jordan", "chol_toon", "fill", "so3",
    "complex", "gr_svd", "diagonal_matrix", "gaussian_elimination",
    "zeros", "swap", "initializer_list", "initializer_list_fail_1",
    "initializer_list_fail_2", "sim3",
)
EXPECTED_COMPILE_FAILURES = {"initializer_list_fail_1", "initializer_list_fail_2"}


class ToonConan(ConanFile):
    name = "toon"
    version = "0.0-git20240623085717.2982ecc"
    description = "Header-only C++ numerical library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/edrosten/TooN"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"
    package_type = "header-library"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.compiler.cppstd) not in ("14", "gnu14", "17", "gnu17"):
            raise ConanInvalidConfiguration("TooN supports C++14 and C++17 configurations")

    def source(self):
        source = self.conan_data["sources"]
        archive = os.environ.get("TOON_SOURCE_ARCHIVE")
        if archive:
            check_sha256(self, archive, source["sha256"])
            unzip(self, archive, destination=self.source_folder,
                  strip_root=True, extract_filter="data")
        else:
            get(self, filename="toon.tar.gz", **source, strip_root=True, extract_filter="data")
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-lapack")
        tc.generate()

    def build(self):
        # This upstream hand-written Makefile has source-relative test paths and
        # config.status writes TooN/internal/config.hh. Run it in an isolated
        # copy of the source tree so build configurations cannot race each other.
        self._source_build_folder = os.path.join(self.build_folder, "toon-source")
        shutil.copytree(self.source_folder, self._source_build_folder,
                        dirs_exist_ok=True)
        toolchain = os.path.join(self.generators_folder,
                                 "conanautotoolstoolchain.sh")
        configure_args = [arg for arg in AutotoolsToolchain(self).configure_args
                          if arg.startswith("--host=")]
        configure_args.append("--disable-lapack")
        source = shlex.quote(self._source_build_folder)
        toolchain = shlex.quote(toolchain)
        configure = shlex.join(["./configure", *configure_args])
        if str(self.settings.os) == "OHOS":
            configure = f"TOON_CONFIG_STATUS_MKDIR=1 {configure}"
        command = (
            f"cd {source} && . {toolchain} && "
            f"{configure} && make testclean && make test"
        )
        self.run(command)
        self._verify_core_test_outputs(self._source_build_folder)

    def _verify_core_test_outputs(self, source_folder):
        tests_dir = Path(source_folder) / "tests"
        results_path = tests_dir / "results"
        if not results_path.is_file():
            raise RuntimeError("TooN did not produce tests/results")
        result_lines = [line.strip() for line in results_path.read_text().splitlines()
                        if line.strip()]
        expected = {f"{name} Passed" for name in CORE_TESTS}
        if len(result_lines) != len(CORE_TESTS) or set(result_lines) != expected:
            raise RuntimeError(f"TooN core result mismatch: {result_lines!r}")
        for name in CORE_TESTS:
            output_path = tests_dir / f"{name}.testout"
            result_path = tests_dir / f"{name}.result"
            expected_path = tests_dir / f"{name}.txt"
            if not output_path.is_file() or not result_path.is_file():
                raise RuntimeError(f"Missing TooN output for {name}")
            if result_path.read_text(errors="replace").strip() != f"{name} Passed":
                raise RuntimeError(f"TooN per-test result is not Passed: {name}")
            output = output_path.read_text(errors="replace")
            if "Crash!!!" in output or " Failed " in output:
                raise RuntimeError(f"TooN test output reports failure: {name}")
            if "Compile error!" in output and name not in EXPECTED_COMPILE_FAILURES:
                raise RuntimeError(f"Unexpected TooN compile failure: {name}")
            if name in EXPECTED_COMPILE_FAILURES:
                if "Compile error!" not in output:
                    raise RuntimeError(f"Expected negative compile test did not fail: {name}")
                if expected_path.read_text(errors="replace").strip() != "Compile error!":
                    raise RuntimeError(f"Expected compile-error fixture changed: {name}")

    def package(self):
        source_build_folder = os.path.join(self.build_folder, "toon-source")
        copy(self, "*", src=os.path.join(source_build_folder, "TooN"),
             dst=os.path.join(self.package_folder, "include", "TooN"))
        copy(self, "COPYING", src=source_build_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "toon")
        self.cpp_info.set_property("cmake_target_name", "toon::toon")
