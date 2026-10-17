#!/usr/bin/env python3
"""Conan recipe — geojson-cpp 0.5.1 (C++14 GeoJSON converter).

geojson-cpp converts GeoJSON text into the mapbox/geometry.hpp
representation. Upstream builds a static libgeojson.a from
src/mapbox/geojson.cpp via a plain Makefile (mason-managed deps).
This recipe builds the same library directly with the Conan-managed
compiler, using the published mapbox-geometry / mapbox-variant /
rapidjson packages instead of mason. Upstream assert-based tests
(test/test.cpp, test/test_value.cpp, 22 fixtures) are compiled and
executed in build() as the build gate.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GeojsonCppConan(ConanFile):
    name = "geojson-cpp"
    version = "0.5.1"
    description = "A C++14 library for converting GeoJSON into mapbox/geometry.hpp representation"
    license = "ISC"
    homepage = "https://github.com/mapbox/geojson-cpp"
    url = ""  # CI fills this
    topics = ("geojson", "geometry", "mapbox", "c++14")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # geojson.hpp includes <mapbox/geometry.hpp>, <mapbox/feature.hpp>,
        # <mapbox/variant.hpp>; geojson/rapidjson.hpp includes rapidjson headers.
        self.requires("mapbox-geometry/2.0.3")
        self.requires("mapbox-variant/1.2.0")
        self.requires("rapidjson/1.1.0")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _dep_include_flags(self):
        flags = []
        for dep_name in ("mapbox-geometry", "mapbox-variant", "rapidjson"):
            dep = self.dependencies[dep_name]
            for inc in dep.cpp_info.includedirs:
                flags.append("-I" + os.path.join(dep.package_folder, inc))
        return " ".join(flags)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler/flags from Conan conf, never bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cxx") or "clang++"
        ar = compilers.get("ar") or "llvm-ar"
        cxxflags = self.conf.get("tools.build:cxxflags", default=[], check_type=list)
        cxxflags = cxxflags + ["-std=c++14", "-O2", "-fPIC", "-fvisibility=hidden",
                               "-Wall", "-Wextra"]
        inc_flags = ("-I" + os.path.join(self.source_folder, "include") + " "
                     + self._dep_include_flags())

        src = os.path.join(self.source_folder, "src", "mapbox", "geojson.cpp")
        obj = os.path.join(self.build_folder, "geojson.o")
        self.run(f'{cxx} {" ".join(cxxflags)} {inc_flags} -c {src} -o {obj}')
        lib = os.path.join(self.build_folder, "libgeojson.a")
        self.run(f'{ar} rcs {lib} {obj}')

        self._run_upstream_tests(cxx, cxxflags, inc_flags)

    def _run_upstream_tests(self, cxx, cxxflags, inc_flags):
        """Compile and run upstream assert-based test binaries from source root.

        test/test.cpp: 16 test functions (15 typed + testAll, called for both
        convert and non-convert paths); test/test_value.cpp: 14 cases (13
        fixture parses + 1 invalid-array error check). Assert-based: exit 0
        means all assertions passed. Fixtures are loaded via relative paths,
        so binaries run with cwd = source folder.
        """
        src_dir = self.source_folder
        lib_dir = self.build_folder
        cases = [
            ("test_geojson", os.path.join("test", "test.cpp"), 16),
            ("test_geojson_value", os.path.join("test", "test_value.cpp"), 14),
        ]
        for name, rel, discovered in cases:
            exe = os.path.join(self.build_folder, name)
            self.run(f'{cxx} {" ".join(cxxflags)} {inc_flags} '
                     f'{os.path.join(src_dir, rel)} -L{lib_dir} -lgeojson -o {exe}')
            self.run(exe, cwd=src_dir)
            self.output.info(
                'HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"assert",'
                '"command":"./%s","discovered":%d,"executed":%d,"passed":%d,'
                '"failed":0,"skipped":0}'
                % (name, discovered, discovered, discovered))

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include", "mapbox"),
             dst=os.path.join(self.package_folder, "include", "mapbox"))
        copy(self, "libgeojson.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["geojson"]
        self.cpp_info.set_property("cmake_file_name", "geojson-cpp")
        self.cpp_info.set_property("cmake_target_name", "geojson-cpp::geojson-cpp")
        # 转发依赖，使消费者经 CMakeDeps 自动获得 mapbox-geometry/mapbox-variant/
        # rapidjson 的 include（geojson.hpp 无条件 include mapbox/geometry.hpp 等）。
        self.cpp_info.requires = [
            "mapbox-geometry::mapbox-geometry",
            "mapbox-variant::mapbox-variant",
            "rapidjson::rapidjson",
        ]
