#!/usr/bin/env python3
"""Conan recipe for the Boost.Stacktrace 1.84.0 noop split package.

Boost.Build cannot target the repository's HarmonyOS environment (E068), so
the single upstream implementation source is compiled directly with the
compiler and archiver supplied by the Conan profile.  The recipe also builds
and runs the six canonical noop targets from the upstream test Jamfile.
"""

import os
import signal
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class BoostStacktraceNoopConan(ConanFile):
    name = "boost1.84-stacktrace_noop"
    version = "1.84.0"
    description = (
        "Boost.Stacktrace 1.84.0 noop static library for HarmonyOS PC"
    )
    license = "BSL-1.0"
    homepage = "https://www.boost.org/doc/libs/1_84_0/libs/stacktrace/"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    # Boost has more than 76,000 files.  Copying the full tree into the build
    # folder is prohibitively slow on HMDFS; the recipe only reads source files
    # after applying the exported patch to Conan's isolated source tree.
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "hdc_runner.py",
            src=os.path.join(self.recipe_folder, "test_package"),
            dst=os.path.join(self.export_sources_folder, "test_package"),
        )

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _compiler_tools(self):
        tools = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        return tools.get("cpp", "clang++"), tools.get("ar", "llvm-ar")

    def _common_flags(self):
        return " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            "-fPIC",
            f'-I"{self.source_folder}"',
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ])

    def _build_type_flags(self):
        if str(self.settings.build_type) == "Debug":
            return "-O0 -g"
        return "-O2 -DNDEBUG"

    def _build_noop_library(self, cxx, ar, flags):
        obj_dir = os.path.join(self.build_folder, "obj_stacktrace_noop")
        os.makedirs(obj_dir, exist_ok=True)
        source = os.path.join(
            self.source_folder, "libs", "stacktrace", "src", "noop.cpp"
        )
        obj = os.path.join(obj_dir, "noop.o")
        library = os.path.join(
            self.build_folder, "libboost_stacktrace_noop.a"
        )
        self.run(
            f'"{cxx}" {flags} {self._build_type_flags()} '
            f'-c "{source}" -o "{obj}"'
        )
        self.run(f'"{ar}" rcs "{library}" "{obj}"')
        return library

    def _run_command(self, command, timeout=300, shell=False):
        process = subprocess.Popen(
            command,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return process.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                process.kill()
            stdout, stderr = process.communicate()
            return -1, stdout, stderr

    def _target_command(self, executable, label):
        hdc = os.environ.get("BOOST_STACKTRACE_NOOP_HDC")
        if not hdc:
            return [executable]

        runner = os.path.join(
            self.source_folder, "test_package", "hdc_runner.py"
        )
        remote_base = os.environ.get(
            "BOOST_STACKTRACE_NOOP_HDC_REMOTE_DIR",
            "/data/local/tmp/boost_stacktrace_noop_1_84_0",
        ).rstrip("/")
        command = [
            sys.executable,
            runner,
            "--hdc",
            hdc,
            "--remote-dir",
            f"{remote_base}/upstream",
            "--label",
            label,
            "--timeout",
            "300",
        ]
        target = os.environ.get("BOOST_STACKTRACE_NOOP_HDC_TARGET")
        if target:
            command.extend(["--target", target])
        command.append(executable)
        return command

    def _run_upstream_tests(self, cxx, flags, library):
        """Build and run all six canonical noop targets from Jamfile.v2."""
        test_dir = os.path.join(
            self.source_folder, "libs", "stacktrace", "test"
        )
        test_impl = os.path.join(test_dir, "test_impl.cpp")
        noop = os.path.join(test_dir, "test_noop.cpp")
        trivial = os.path.join(test_dir, "test_trivial.cpp")
        cases = [
            (
                "noop_ho",
                [noop, test_impl],
                "-O0 -g -DBOOST_STACKTRACE_USE_NOOP",
                "",
            ),
            (
                "trivial_noop_ho",
                [trivial],
                "-O0 -g -DBOOST_STACKTRACE_USE_NOOP",
                "",
            ),
            (
                "noop_lib",
                [noop, test_impl],
                "-O0 -g -DBOOST_STACKTRACE_LINK",
                library,
            ),
            (
                "trivial_noop_lib",
                [trivial],
                "-O0 -g -DBOOST_STACKTRACE_LINK",
                library,
            ),
            (
                "noop_ho_no_dbg",
                [noop, test_impl],
                "-O2 -DNDEBUG -DBOOST_STACKTRACE_USE_NOOP",
                "",
            ),
            (
                "noop_lib_no_dbg",
                [noop, test_impl],
                "-O2 -DNDEBUG -DBOOST_STACKTRACE_LINK",
                library,
            ),
        ]

        report = []
        failures = []
        for label, sources, variant_flags, link_library in cases:
            executable = os.path.join(
                self.build_folder, f"upstream_{label}"
            )
            source_args = " ".join(f'"{source}"' for source in sources)
            link_args = f' "{link_library}"' if link_library else ""
            command = (
                f'"{cxx}" {flags} {variant_flags} {source_args}'
                f'{link_args} -static-libstdc++ -o "{executable}"'
            )
            compile_code = self.run(command, ignore_errors=True)
            if compile_code != 0:
                message = f"{label} COMPILE_FAIL: exit code {compile_code}"
                report.append(f"FAIL {message}")
                failures.append(message)
                continue

            run_code, run_output, run_error = self._run_command(
                self._target_command(executable, label)
            )
            details = (run_output or run_error).strip().splitlines()
            message = f"{label} rc={run_code}"
            if details:
                message += f" ({details[-1]})"
            report.append(
                f"{'PASS' if run_code == 0 else 'FAIL'} {message}"
            )
            if run_code != 0:
                failures.append(message)

        report.append(
            f"TOTAL {len(cases)}: {len(cases) - len(failures)} passed / "
            f"{len(failures)} failed"
        )
        report_path = os.path.join(
            self.build_folder, "upstream-tests-report.txt"
        )
        with open(report_path, "w", encoding="utf-8") as stream:
            stream.write("\n".join(report) + "\n")
        for line in report:
            self.output.info(f"[upstream-tests] {line}")

        if failures:
            raise ConanInvalidConfiguration(
                "Boost.Stacktrace noop upstream tests failed: "
                + "; ".join(failures)
            )

    def build(self):
        cxx, ar = self._compiler_tools()
        flags = self._common_flags()
        library = self._build_noop_library(cxx, ar, flags)
        self._run_upstream_tests(cxx, flags, library)

    def package(self):
        copy(
            self,
            "boost/*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libboost_stacktrace_noop.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "upstream-tests-report.txt",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "res", "reports"),
        )

    def package_info(self):
        self.cpp_info.set_property(
            "cmake_file_name", "boost1.84-stacktrace_noop"
        )

        headers = self.cpp_info.components[
            "boost1.84_stacktrace_noop_headers"
        ]
        headers.includedirs = ["include"]
        headers.defines = [
            "BOOST_ALL_NO_LIB",
            "BOOST_STACKTRACE_USE_NOOP",
            "BOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ]
        headers.set_property(
            "cmake_target_name", "boost1.84-stacktrace_noop::headers"
        )

        component = self.cpp_info.components[
            "boost1.84_stacktrace_noop"
        ]
        component.includedirs = []
        component.libs = ["boost_stacktrace_noop"]
        component.defines = ["BOOST_STACKTRACE_LINK"]
        component.requires = ["boost1.84_stacktrace_noop_headers"]
        component.set_property(
            "cmake_target_name",
            "boost1.84-stacktrace_noop::stacktrace_noop",
        )
