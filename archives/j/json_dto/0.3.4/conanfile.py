#!/usr/bin/env python3
"""Conan recipe — json_dto 0.3.4 (header-only C++ JSON conversion library).

json_dto converts C++ objects to/from JSON on top of RapidJSON. It is a
pure header-only library (INTERFACE CMake target json-dto::json-dto); no
compilation is needed for the library itself. Upstream Catch2-based unit
tests (20 ctest targets, 711 assertions) are compiled and run in build()
to provide HMBS upstream-test evidence, mirroring the house pattern used
by ableton-link / spectra.

The recipe keeps upstream source behavior (headers only). It depends on
rapidjson/1.1.0 (published in the ohpcd registry) whose headers are
required by json_dto/pub.hpp, and re-exports the two upstream compile
definitions (RAPIDJSON_HAS_STDSTRING / RAPIDJSON_HAS_CXX11_RVALUE_REFS)
that consumers must see to enable std::string interop.
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy


class JsonDtoConan(ConanFile):
    name = "json_dto"
    version = "0.3.4"
    description = "A tiny helper library for converting data between C++ structures and JSON"
    license = "MIT"
    homepage = "https://github.com/Stiffstream/json_dto"
    url = ""  # CI fills this
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("rapidjson/1.1.0")

    def build_requirements(self):
        self.test_requires("catch2/2.13.10")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The official v.0.3.4 tag tarball keeps the build tree under a
        # top-level dev/ directory (project(), json_dto/, sample/, test/,
        # cmake/ all live there); flatten it so CMakeLists.txt sits at the
        # source root like the upstream repository layout expects.
        dev = os.path.join(self.source_folder, "dev")
        if os.path.isdir(dev):
            for item in os.listdir(dev):
                shutil.move(os.path.join(dev, item), self.source_folder)
            shutil.rmtree(dev)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["JSON_DTO_TEST"] = "ON"
        tc.variables["JSON_DTO_SAMPLE"] = "OFF"
        # Upstream test tree includes <rapidjson/...> and <catch2/catch.hpp>
        # directly without find_package(); inject both include dirs so the
        # test targets compile against the conan-provided packages.
        include_dirs = []
        for dep_name in ("rapidjson", "catch2"):
            dep = self.dependencies[dep_name]
            for inc in getattr(dep.cpp_info, "includedirs", []) or ["include"]:
                include_dirs.append(os.path.join(dep.package_folder, inc))
        flags = " ".join("-I" + d for d in include_dirs)
        if flags:
            tc.variables["CMAKE_CXX_FLAGS"] = flags
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream ctest suite (20 targets) and emit the HMBS marker."""
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        proc = subprocess.run(
            [bash, "-c", "ctest --output-on-failure"],
            cwd=self.build_folder, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, timeout=1800)
        output = proc.stdout
        # ctest summary line: "100% tests passed, 0 tests failed out of 20"
        m = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", output)
        if m is None:
            self.output.error("upstream ctest summary not found:\n" + output[-2000:])
            raise RuntimeError("upstream ctest produced no summary")
        total = int(m.group(3))
        failed = int(m.group(2))
        passed = total - failed
        upstream = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "catch2",
            "command": "ctest --output-on-failure",
            "discovered": total,
            "executed": total,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if failed != 0:
            self.output.error(output[-3000:])
            raise RuntimeError("upstream tests failed")

    def package(self):
        # Header-only library: ship json_dto/{pub,validators}.hpp as
        # include/json_dto/, preserving the upstream include layout.
        copy(self, "pub.hpp",
             src=os.path.join(self.source_folder, "json_dto"),
             dst=os.path.join(self.package_folder, "include", "json_dto"))
        copy(self, "validators.hpp",
             src=os.path.join(self.source_folder, "json_dto"),
             dst=os.path.join(self.package_folder, "include", "json_dto"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "json-dto")
        self.cpp_info.set_property("cmake_target_name", "json-dto::json-dto")
        # Consumers compile against json_dto headers which include
        # <rapidjson/...>; propagate the header dependency transitively.
        self.cpp_info.requires = ["rapidjson::rapidjson"]
        # Upstream interface target defines these for rapidjson std::string
        # interop; consumers must see them too.
        self.cpp_info.defines = [
            "RAPIDJSON_HAS_STDSTRING=1",
            "RAPIDJSON_HAS_CXX11_RVALUE_REFS=1",
        ]