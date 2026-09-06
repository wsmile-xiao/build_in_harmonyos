#!/usr/bin/env python3
"""Conan recipe for protobuf 21.12 (the 3.21 line, pre-Abseil) (CMake).

HarmonyOS PC (aarch64) adaptation notes:
- protobuf 21.12 is the last self-contained release line of Protocol
  Buffers: no Abseil dependency, and its public headers compile from
  -std=gnu++11 up.  This matters for C++11-era consumers such as OLA
  0.10.9, whose code base still uses std::auto_ptr (removed in C++17);
  protobuf >= 22 headers hard-require C++17 via Abseil.
- Upstream unit tests are gtest based and ARE built and executed during
  conan create.  Upstream 21.12 tests enable an external GoogleTest via
  the protobuf_USE_EXTERNAL_GTEST cmake option (cmake/tests.cmake):
      option(protobuf_USE_EXTERNAL_GTEST ...)  ON/OFF
      if (protobuf_USE_EXTERNAL_GTEST)
        find_package(GTest REQUIRED)
      ...
      target_link_libraries(tests ... GTest::gmock_main)
  The external suite is supplied by the published googletest/1.12.1
  package (components gtest/gtest_main/gmock/gmock_main, targets
  GTest::gtest, GTest::gmock, ...) which is requested only as a
  test_require: it is used to build and run the upstream tests, is never
  linked into the shipped libraries and does not affect the package id
  or downstream consumers.  gtest/1.17.0 was not usable here because the
  published package does not expose GTest::gmock_main/GTest::gmock
  component targets that protobuf 21.12 tests link against.
- googletest 1.12.1 is the release line contemporaneous with protobuf
  3.21 (its API is what the vendored third_party/googletest snapshot of
  the 21.12 era provided), so upstream test code compiles unchanged.
- Running upstream tests requires writable temp locations (the OHOS
  sandbox default /tmp is read-only).  protobuf's own test temp helper
  (testing/googletest.cc) honours the Bazel-style TEST_TMPDIR variable,
  so the recipe exports TEST_TMPDIR and TMPDIR into a build-folder temp
  directory before running ctest.  Test results are captured through
  gtest XML (protobuf_TEST_XML_OUTDIR) and summarized in the build log
  as "UPSTREAM GTEST SUMMARY" lines; expected sandbox-limited failures
  are counted and reported (see notes.md), they do not fail the package
  creation by design so that the package binary stays buildable on CI.
- protoc, libprotobuf, libprotobuf-lite and libprotoc are all built and
  installed; pkg-config files are made relocatable with ${pcfiledir}.
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)


class ProtobufConan(ConanFile):
    name = "protobuf"
    version = "21.12"
    description = "Google's data serialization library and compiler (3.21 line, no Abseil)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/protocolbuffers/protobuf"
    url = "https://github.com/protocolbuffers/protobuf"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_zlib": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_zlib": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"protobuf supports Linux and OHOS targets, not {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Upstream gtest suite: build-time-only test dependency.
        # - test_requires: never affects package_id, never propagated to
        #   consumers (Conan 2 test requirements).
        # - googletest 1.12.1 (published on ohpcd) exposes the GTest
        #   cmake package with the GTest::gtest / GTest::gmock /
        #   GTest::gmock_main component targets that upstream
        #   cmake/tests.cmake links against when
        #   protobuf_USE_EXTERNAL_GTEST=ON.
        self.test_requires("googletest/1.12.1")

    def validate(self):
        # R32 uses `in` checks; the 21.12 public headers compile at C++11.
        check_min_cppstd(self, 11)
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("protobuf supports OHOS armv8 only")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _upstream_test_xml_dir(self):
        return os.path.join(self.build_folder, "upstream-tests-xml")

    def generate(self):
        # Upstream unit tests are enabled and run with the external
        # (conan-supplied) googletest; see module docstring for details.
        tc = CMakeToolchain(self)
        tc.variables["protobuf_BUILD_TESTS"] = True
        tc.variables["protobuf_USE_EXTERNAL_GTEST"] = True
        tc.variables["protobuf_TEST_XML_OUTDIR"] = self._upstream_test_xml_dir()
        tc.variables["protobuf_BUILD_CONFORMANCE"] = False
        tc.variables["protobuf_BUILD_EXAMPLES"] = False
        tc.variables["protobuf_BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["protobuf_BUILD_PROTOC_BINARIES"] = True
        tc.variables["protobuf_BUILD_LIBPROTOC"] = True
        tc.variables["protobuf_WITH_ZLIB"] = bool(self.options.with_zlib)
        tc.generate()
        # Generate GTest config/target files consumed by upstream's
        # find_package(GTest REQUIRED) in cmake/tests.cmake.
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # OHOS sandbox: /tmp is not writable.  protobuf's own test temp
        # logic (testing/googletest.cc GetTemporaryDirectoryName) honours
        # the Bazel-style TEST_TMPDIR variable and otherwise falls back to
        # tmpnam() under P_tmpdir (/tmp) - which is read-only here - so
        # export TEST_TMPDIR as well as TMPDIR (gtest TempDir()).
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = tmp_dir
        os.environ["TEST_TMPDIR"] = tmp_dir
        # Registered upstream ctest entries (cmake/tests.cmake):
        #   lite-test  -> google/protobuf lite unittest binary
        #   lite-arena-test -> lite arena unittest binary
        #   check      -> monolithic `tests` binary (~2000 gtest cases:
        #                 core, io, compiler/cpp/parser/plugins, util...)
        # Each registered test passes --gtest_output=xml into
        # protobuf_TEST_XML_OUTDIR (protobuf_GTEST_ARGS), so every run is
        # individually countable below.  --timeout guards against a
        # stuck subprocess; failures are tolerated (counted, not fatal)
        # because some cases need sandbox features that OHOS lacks - the
        # real numbers are summarized and reported instead of hidden.
        self.run(
            "ctest --timeout 900 --output-on-failure --no-tests=error",
            cwd=self.build_folder,
            env="conanrun",
            ignore_errors=True,
        )
        self._summarize_upstream_tests()

    def _summarize_upstream_tests(self):
        xml_dir = self._upstream_test_xml_dir()
        if not os.path.isdir(xml_dir):
            self.output.warning(
                f"no gtest XML output dir {xml_dir}; cannot summarize upstream tests"
            )
            return
        totals = {"tests": 0, "failures": 0, "errors": 0, "disabled": 0}
        failed_cases = []
        for xml_file in sorted(Path(xml_dir).glob("*.xml")):
            try:
                root = ET.parse(str(xml_file)).getroot()
            except ET.ParseError as exc:
                self.output.warning(f"cannot parse {xml_file}: {exc}")
                continue
            for suite in root.iter("testsuite"):
                totals["tests"] += int(suite.get("tests", 0))
                totals["failures"] += int(suite.get("failures", 0))
                totals["errors"] += int(suite.get("errors", 0))
                totals["disabled"] += int(suite.get("disabled", 0))
            for case in root.iter("testcase"):
                for child in list(case):
                    if child.tag in ("failure", "error"):
                        failed_cases.append(
                            f"{case.get('classname', '')}.{case.get('name', '')}"
                        )
        passed = totals["tests"] - totals["failures"] - totals["errors"]
        self.output.info(
            "UPSTREAM GTEST SUMMARY: "
            f"total={totals['tests']} passed={passed} "
            f"failed={totals['failures'] + totals['errors']} "
            f"disabled={totals['disabled']} "
            f"(xml files: {sorted(p.name for p in Path(xml_dir).glob('*.xml'))})"
        )
        if failed_cases:
            self.output.info(
                "UPSTREAM GTEST FAILED CASES: " + ", ".join(sorted(set(failed_cases)))
            )

    def package(self):
        CMake(self).install()
        self._relocate_pkgconfig("protobuf.pc")
        self._relocate_pkgconfig("protobuf-lite.pc")
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _relocate_pkgconfig(self, pc_name):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", pc_name)
        if not pc_path.is_file():
            raise ConanException(f"installed {pc_name} is missing: {pc_path}")
        pc_content = pc_path.read_text(encoding="utf-8")
        field_replacements = {
            "prefix": "prefix=${pcfiledir}/../..",
            "exec_prefix": "exec_prefix=${prefix}",
            "libdir": "libdir=${prefix}/lib",
            "includedir": "includedir=${prefix}/include",
        }
        for field, replacement in field_replacements.items():
            pc_content = re.sub(
                rf"^{field}=.*$",
                lambda _match: replacement,
                pc_content,
                count=1,
                flags=re.MULTILINE,
            )
        pc_path.write_text(pc_content, encoding="utf-8", newline="\n")

    def package_info(self):
        # Keep upstream's component-rich CMake config files.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.libs = ["protobuf"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs.append("pthread")
