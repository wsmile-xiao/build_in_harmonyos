#!/usr/bin/env python3
"""Conan recipe for the wxWidgets 3.3.3 base libraries, OHOS revision 1."""

import glob
import hashlib
import inspect
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
)


class WxWidgetsConan(ConanFile):
    name = "wxwidgets"
    version = "3.3.3.1"
    description = "Cross-platform C++ GUI and utility framework"
    license = "wxWindows"
    homepage = "https://www.wxwidgets.org/"
    url = "https://github.com/wxWidgets/wxWidgets"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    _upstream_test_count = 429
    _upstream_inventory_sha256 = (
        "2214c00249801b8f0b2b1b7b72c6fdf6c00217d32da3a3b777c2d8afabe73ebe"
    )
    _expected_skip_schema = "wxwidgets-3.3.3-expected-skips-v2"
    _expected_skips = (
        (
            "Dir::Exists",
            "tests/file/dir.cpp",
            "directory_fixture_unreadable",
            "Dir::Exists",
        ),
        (
            "Dir::GetName",
            "tests/file/dir.cpp",
            "root_directory_unreadable",
            "Dir::GetName",
        ),
        (
            "wxFileName::CreateTempFileName",
            "tests/filename/filenametest.cpp",
            "system_tmp_unwritable",
            "wxFileName::CreateTempFileName",
        ),
        (
            "wxFileName::Exists/socket",
            "tests/filename/filenametest.cpp",
            "unix_socket_unavailable",
            "wxFileName::Exists",
        ),
        (
            "wxFileName::Exists/fifo",
            "tests/filename/filenametest.cpp",
            "fifo_unavailable",
            "wxFileName::Exists",
        ),
        (
            "wxFileName::SameAs",
            "tests/filename/filenametest.cpp",
            "symlink_unavailable",
            "wxFileName::SameAs",
        ),
        (
            "wxFileName::Symlinks",
            "tests/filename/filenametest.cpp",
            "symlink_unavailable",
            "wxFileName::Symlinks",
        ),
        (
            "wxFileSystemWatcher::Trees",
            "tests/fswatcher/fswatchertest.cpp",
            "symlink_unavailable",
            "wxFileSystemWatcher::Trees",
        ),
        (
            "wxStopWatch::RestartBug",
            "tests/events/stopwatch.cpp",
            "timer_scheduler_jitter",
            "StopWatchTestCase",
        ),
        (
            "wxUILocale::GetInfo",
            "tests/intl/intltest.cpp",
            "locale_data_unavailable",
            "wxUILocale::GetInfo",
        ),
        (
            "wxUILocale::CompareStrings",
            "tests/intl/intltest.cpp",
            "locale_collation_unavailable",
            "wxUILocale::CompareStrings",
        ),
        (
            "wxMBConv::FallbackMultibyte",
            "tests/mbconv/convautotest.cpp",
            "encoding_unavailable",
            "MBConvTestCase",
        ),
        (
            "wxMBConv::StreamFallbackMultibyte",
            "tests/mbconv/convautotest.cpp",
            "encoding_unavailable",
            "MBConvTestCase",
        ),
        (
            "wxMBConv::CP932Tests",
            "tests/mbconv/mbconvtest.cpp",
            "encoding_unavailable",
            "MBConvTestCase",
        ),
        (
            "wxMBConv::CP1252Tests",
            "tests/mbconv/mbconvtest.cpp",
            "encoding_unavailable",
            "MBConvTestCase",
        ),
        (
            "wxMBConv::Latin1Tests",
            "tests/mbconv/mbconvtest.cpp",
            "encoding_unavailable",
            "MBConvTestCase",
        ),
        (
            "wxMBConv::FontmapTests",
            "tests/mbconv/mbconvtest.cpp",
            "encoding_unavailable",
            "MBConvTestCase",
        ),
        (
            "wxMBConv::FromWCharTests",
            "tests/mbconv/mbconvtest.cpp",
            "encoding_unavailable",
            "MBConvTestCase",
        ),
        (
            "wxMBConv::NonBMPCharTests",
            "tests/mbconv/mbconvtest.cpp",
            "encoding_unavailable",
            "MBConvTestCase",
        ),
        (
            "NumFormatter::LongToString",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatter::LongToString",
        ),
        (
            "NumFormatter::LongLongToString",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatter::LongLongToString",
        ),
        (
            "NumFormatter::DoubleToString",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatter::DoubleToString",
        ),
        (
            "NumFormatter::LongFromString",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatter::LongFromString",
        ),
        (
            "NumFormatter::LongLongFromString",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatter::LongLongFromString",
        ),
        (
            "NumFormatter::ULongLongFromString",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatter::ULongLongFromString",
        ),
        (
            "NumFormatter::DoubleFromString",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatter::DoubleFromString",
        ),
        (
            "NumFormatterAlternateTestCase::LongToString",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatterAlternateTestCase::LongToString",
        ),
        (
            "NumFormatterAlternateTestCase::LongLongToString",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatterAlternateTestCase::LongLongToString",
        ),
        (
            "NumFormatterAlternateTestCase::DoubleToString",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatterAlternateTestCase::DoubleToString",
        ),
        (
            "NumFormatterAlternateTestCase::NoTrailingZeroes",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatterAlternateTestCase::NoTrailingZeroes",
        ),
        (
            "NumFormatterAlternateTestCase::LongFromString",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatterAlternateTestCase::LongFromString",
        ),
        (
            "NumFormatterAlternateTestCase::LongLongFromString",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatterAlternateTestCase::LongLongFromString",
        ),
        (
            "NumFormatterAlternateTestCase::DoubleFromString",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "NumFormatterAlternateTestCase::DoubleFromString",
        ),
        (
            "FormatNumberTestCase::PositiveIntegers",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "FormatNumberTestCase::PositiveIntegers",
        ),
        (
            "FormatNumberTestCase::NegativeIntegers",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "FormatNumberTestCase::NegativeIntegers",
        ),
        (
            "FormatNumberTestCase::PositiveReals",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "FormatNumberTestCase::PositiveReals",
        ),
        (
            "FormatNumberTestCase::NegativeReals",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "FormatNumberTestCase::NegativeReals",
        ),
        (
            "FormatNumberAlternateTestCase::PositiveIntegers",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "FormatNumberAlternateTestCase::PositiveIntegers",
        ),
        (
            "FormatNumberAlternateTestCase::NegativeIntegers",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "FormatNumberAlternateTestCase::NegativeIntegers",
        ),
        (
            "FormatNumberAlternateTestCase::PositiveReals",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "FormatNumberAlternateTestCase::PositiveReals",
        ),
        (
            "FormatNumberAlternateTestCase::NegativeReals",
            "tests/strings/numformatter.cpp",
            "locale_number_format_unavailable",
            "FormatNumberAlternateTestCase::NegativeReals",
        ),
        (
            "XmlTestCase::CDATA",
            "tests/xml/xmltest.cpp",
            "xml_encoding_unavailable",
            "XmlTestCase",
        ),
        (
            "XmlTestCase::PI",
            "tests/xml/xmltest.cpp",
            "xml_encoding_unavailable",
            "XmlTestCase",
        ),
        (
            "XmlTestCase::DetachRoot",
            "tests/xml/xmltest.cpp",
            "xml_encoding_unavailable",
            "XmlTestCase",
        ),
    )
    _expected_skip_inventory_sha256 = (
        "70855349b10167b33ba26b7554072efee7624a08f24fb862d91a7c89dc03c9e9"
    )
    _expected_skip_pattern = re.compile(
        r"^[ \t]*(?:\d+:[ \t]*)?(?:warning:[ \t]*)?WX_EXPECTED_SKIP:"
        r"id=([^;]+);path=([^;]+);reason=([A-Za-z0-9_]+)\r?$",
        re.MULTILINE,
    )

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "wxWidgets is a system same-name library and must be packaged statically"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["wxBUILD_SHARED"] = False
        tc.variables["wxBUILD_SAMPLES"] = "OFF"
        tc.variables["wxBUILD_DEMOS"] = False
        tc.variables["wxBUILD_BENCHMARKS"] = False
        tc.variables["wxBUILD_TESTS"] = "CONSOLE_ONLY"
        tc.variables["wxBUILD_LOCALES"] = False
        tc.variables["wxBUILD_PRECOMP"] = "OFF"
        tc.variables["wxBUILD_INSTALL_USE_SYMLINK"] = False
        tc.variables["wxUSE_GUI"] = False
        tc.variables["wxUSE_SYS_LIBS"] = False
        tc.variables["wxUSE_LIBLZMA"] = False
        if str(self.settings.os) in ("Linux", "OHOS"):
            tc.cache_variables["UNIX"] = True
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        if self.settings.os == "OHOS":
            cmake.build(cli_args=["-j1"])
        else:
            cmake.build()

        if not can_run(self):
            raise ConanInvalidConfiguration(
                "wxWidgets upstream tests require an executable target runtime; "
                "a cross-built package cannot claim test success"
            )

        test_executable = self._find_test_executable()
        if self.settings.os == "OHOS":
            self._sign_executable(test_executable)
        previous_test_locale = os.environ.get("WX_TEST_LOCALE")
        os.environ["WX_TEST_LOCALE"] = "C.UTF-8"
        try:
            upstream_inventory = self._audit_upstream_inventory(test_executable)
            self._run_upstream_tests(upstream_inventory)
        finally:
            if previous_test_locale is None:
                os.environ.pop("WX_TEST_LOCALE", None)
            else:
                os.environ["WX_TEST_LOCALE"] = previous_test_locale

    def _audit_upstream_inventory(self, test_executable):
        result = subprocess.run(
            [test_executable, "--list-tests"],
            cwd=os.path.dirname(test_executable),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.stdout:
            self.output.info(result.stdout.rstrip())
        if result.stderr:
            self.output.error(result.stderr.rstrip())

        expected_returncode = min(self._upstream_test_count, 255)
        if result.returncode != expected_returncode:
            raise ConanInvalidConfiguration(
                "Unexpected Catch2 list return code: "
                f"expected {expected_returncode}, got {result.returncode}"
            )
        if result.stderr:
            raise ConanInvalidConfiguration(
                "Catch2 test inventory wrote unexpected stderr output"
            )

        lines = result.stdout.splitlines()
        header_indexes = [
            index
            for index, line in enumerate(lines)
            if line == "All available test cases:"
        ]
        footer_pattern = re.compile(r"^(\d+) test cases$")
        footers = [
            (index, footer_pattern.fullmatch(line))
            for index, line in enumerate(lines)
            if footer_pattern.fullmatch(line)
        ]
        if len(header_indexes) != 1 or len(footers) != 1:
            raise ConanInvalidConfiguration(
                "Expected exactly one Catch2 inventory header and footer"
            )

        header_index = header_indexes[0]
        footer_index, footer_match = footers[0]
        footer_count = int(footer_match.group(1))
        if footer_index <= header_index or footer_count != self._upstream_test_count:
            raise ConanInvalidConfiguration(
                "Catch2 inventory footer does not match the expected 429 cases"
            )

        test_names = [
            line[2:]
            for line in lines[header_index + 1 : footer_index]
            if re.match(r"^  \S", line)
        ]
        if len(test_names) != self._upstream_test_count:
            raise ConanInvalidConfiguration(
                "Catch2 inventory must contain 429 test cases"
            )

        inventory = ("\n".join(test_names) + "\n").encode("utf-8")
        inventory_sha256 = hashlib.sha256(inventory).hexdigest()
        if inventory_sha256 != self._upstream_inventory_sha256:
            raise ConanInvalidConfiguration(
                "Catch2 ordered inventory digest does not match wxWidgets 3.3.3"
            )

        self.output.info(
            "Validated complete upstream inventory: "
            f"{self._upstream_test_count} Catch2 test cases"
        )
        return tuple(test_names)

    def _run_upstream_tests(self, upstream_inventory):
        canonical = "".join("|".join(item) + "\n" for item in self._expected_skips)
        inventory_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if inventory_sha256 != self._expected_skip_inventory_sha256:
            raise ConanInvalidConfiguration(
                "Expected-skip inventory digest does not match wxWidgets 3.3.3"
            )

        expected_by_marker = {}
        for skip_id, path, reason, case_id in self._expected_skips:
            marker = (skip_id, path, reason)
            if marker in expected_by_marker:
                raise ConanInvalidConfiguration(
                    "Duplicate expected-skip marker contract: "
                    + "/".join(marker)
                )
            expected_by_marker[marker] = case_id

        upstream_cases = set(upstream_inventory)
        expected_case_ids = set(expected_by_marker.values())
        unknown_case_ids = expected_case_ids - upstream_cases
        if unknown_case_ids:
            raise ConanInvalidConfiguration(
                "Expected-skip case ID missing from the audited upstream inventory: "
                + ", ".join(sorted(unknown_case_ids))
            )

        result = subprocess.run(
            [
                "ctest",
                "--verbose",
                "--output-on-failure",
                "--no-tests=error",
            ],
            cwd=self.build_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        output = "\n".join(part for part in (result.stdout, result.stderr) if part)
        if output:
            self.output.info(output.rstrip())
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                f"CTest failed with return code {result.returncode}"
            )

        observed = [
            match.groups() for match in self._expected_skip_pattern.finditer(output)
        ]
        marker_prefix_count = output.count("WX_EXPECTED_SKIP")
        if marker_prefix_count != len(observed):
            raise ConanInvalidConfiguration(
                "Malformed WX_EXPECTED_SKIP marker in upstream test output"
            )
        observed_set = set(observed)
        if len(observed) != len(observed_set):
            raise ConanInvalidConfiguration("Duplicate WX_EXPECTED_SKIP marker")
        unknown = observed_set - set(expected_by_marker)
        if unknown:
            raise ConanInvalidConfiguration(
                "Unexpected WX_EXPECTED_SKIP marker(s): "
                + ", ".join("/".join(item) for item in sorted(unknown))
            )

        skip_events = len(observed)
        skipped_case_ids = {
            expected_by_marker[marker] for marker in observed_set
        }
        skipped_cases = len(skipped_case_ids)
        passed = self._upstream_test_count - skipped_cases
        nonfailed = passed + skipped_cases
        if passed < 0 or nonfailed != self._upstream_test_count:
            raise ConanInvalidConfiguration("Invalid upstream skip accounting")
        self.output.info(
            "WX_EXPECTED_SKIP_SCHEMA="
            f"{self._expected_skip_schema};"
            f"allowed_events={len(expected_by_marker)};"
            f"allowed_cases={len(expected_case_ids)};"
            f"observed_events={skip_events};"
            f"observed_cases={skipped_cases}"
        )
        self.output.info(
            "WX_TEST_SUMMARY "
            f"total={self._upstream_test_count};passed={passed};"
            f"skipped={skipped_cases};failed=0;nonfailed={nonfailed};"
            f"expected_skip_events={skip_events};"
            f"expected_skip_cases={skipped_cases}"
        )
        self.output.info(
            f"{passed}/{self._upstream_test_count} PASS; "
            f"{skipped_cases}/{self._upstream_test_count} SKIP; "
            f"{nonfailed}/{self._upstream_test_count} NONFAILED"
        )

    def _find_test_executable(self):
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        candidates = [
            path
            for path in glob.glob(
                os.path.join(self.build_folder, "**", f"test_base{suffix}"),
                recursive=True,
            )
            if os.path.isfile(path)
        ]
        if len(candidates) != 1:
            raise ConanInvalidConfiguration(
                f"Expected one upstream test_base executable, found {len(candidates)}"
            )
        return candidates[0]

    def _run_fail_closed(self, command, **kwargs):
        parameters = inspect.signature(self.run).parameters
        if "ignore_errors" in parameters:
            kwargs["ignore_errors"] = False
        elif "check" in parameters:
            kwargs["check"] = True
        else:
            raise ConanInvalidConfiguration(
                "Unsupported ConanFile.run API: expected ignore_errors or check"
            )
        self.run(command, **kwargs)

    def _sign_executable(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS upstream tests require llvm-objcopy and binary-sign-tool"
            )

        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self._run_fail_closed(
                f'"{objcopy}" --remove-section .codesign "{temporary}"'
            )
            self._run_fail_closed(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "licence.txt",
            src=os.path.join(self.source_folder, "docs"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "wxWidgets")
        self.cpp_info.set_property("cmake_target_name", "wxWidgets::wxWidgets")
        self.cpp_info.set_property("pkg_config_name", "wx-baseu-3.3")

        config_dirs = glob.glob(
            os.path.join(self.package_folder, "lib", "wx", "include", "*")
        )
        self.cpp_info.includedirs = ["include/wx-3.3"] + [
            os.path.relpath(path, self.package_folder).replace(os.sep, "/")
            for path in config_dirs
            if os.path.isdir(path)
        ]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        def link_rank(library):
            if "_net-" in library:
                return 0
            if "wx_base" in library:
                return 1
            if "wxregex" in library:
                return 2
            if "wxzlib" in library:
                return 3
            if "wxexpat" in library:
                return 4
            return 5

        self.cpp_info.libs = sorted(collect_libs(self), key=link_rank)
        if self.settings.os == "OHOS":
            self.cpp_info.system_libs = ["pthread", "dl"]
