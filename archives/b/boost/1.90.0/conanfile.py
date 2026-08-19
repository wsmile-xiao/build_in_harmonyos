#!/usr/bin/env python3
"""Conan recipe for boost 1.90.0 — header-only + Boost.Test static library.

Boost is header-only for most libraries (b2 build system incompatible with OHOS).
Headers are always installed. The only compiled Boost library that is mandatory for
consumers is Boost.Test (unit_test_framework) -> libboost_unit_test_framework.

This recipe compiles the Boost.Test static library from libs/test/src/*.cpp using the
Conan default OHOS compiler (no b2 needed), packages it, and exports the Conan component
`unit_test_framework` with the CMake target `Boost::unit_test_framework`.
"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.build import cross_building
from conan.tools.scm import Version


class BoostConan(ConanFile):
    name = "boost"
    version = "1.90.0"
    description = "Boost C++ Libraries 1.90.0 (header-only + Boost.Test static lib)"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""

    # Not header-only: we ship one compiled static Boost library (Boost.Test).
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "header_only": [True, False],
    }
    default_options = {
        "shared": False,
        "header_only": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _load_libboost_test_sources(self):
        """Return the Boost.Test translation units to compile (from libs/test/src)."""
        # Keep the order and set identical to the upstream Boost.Test
        # libs/test/build/CMakeLists.txt BOOST_UTF_SRC list.
        names = [
            "compiler_log_formatter",
            "debug",
            "decorator",
            "execution_monitor",
            "framework",
            "junit_log_formatter",
            "plain_report_formatter",
            "progress_monitor",
            "results_collector",
            "results_reporter",
            "test_framework_init_observer",
            "test_tools",
            "test_tree",
            "unit_test_log",
            "unit_test_main",
            "unit_test_monitor",
            "unit_test_parameters",
            "xml_log_formatter",
            "xml_report_formatter",
        ]
        src_dir = os.path.join(self.source_folder, "libs", "test", "src")
        return [os.path.join(src_dir, n + ".cpp") for n in names], src_dir

    def build(self):
        apply_conandata_patches(self)
        if self.options.header_only:
            # Keep header-only behavior (no compiled lib).
            return

        # Locate the OHOS compiler executables from the Conan toolchain environment.
        cxx = os.environ.get("CXX") or os.environ.get("CXXFLAGS") and None or "clang++"
        # Prefer the Conan-configured compiler executables if set in conf.
        cc = self.conf.get("tools.build:compiler_executables", default={})
        if cc and "cpp" in cc:
            cxx = cc["cpp"]

        srcs, src_dir = self._load_libboost_test_sources()
        include_dirs = [
            os.path.join(self.source_folder, "libs", "test", "include"),
            self.source_folder,        # boost/ root (for <boost/...> includes)
        ]

        obj_out = os.path.join(self.build_folder, "boost-test-obj")
        os.makedirs(obj_out, exist_ok=True)

        cxxflags = ["-std=gnu++14", "-O2", "-DBOOST_TEST_ALTERNATIVE_INIT_API"]
        include_args = []
        for inc in include_dirs:
            include_args.append("-I" + inc)

        objects = []
        for src in srcs:
            base = os.path.splitext(os.path.basename(src))[0]
            obj = os.path.join(obj_out, base + ".o")
            self.run("%s %s %s -c %s -o %s" % (
                cxx, " ".join(cxxflags), " ".join(include_args), src, obj))
            objects.append(obj)

        libdir = os.path.join(self.build_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        libname = "libboost_unit_test_framework.a"
        libout = os.path.join(libdir, libname)
        self.run("ar rcs %s %s" % (libout, " ".join(objects)))

    def package(self):
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        if not self.options.header_only:
            copy(self, "libboost_unit_test_framework.a",
                 src=os.path.join(self.build_folder, "lib"),
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        if self.options.header_only:
            self.cpp_info.libdirs = []
            return

        self.cpp_info.libdirs = ["lib"]
        # Canonical Boost CMake/Conan component export:
        #   - find_package(Boost COMPONENTS unit_test_framework)
        #   - target Boost::unit_test_framework (canonical capital-B namespace)
        #   - pkg-config name libboost_unit_test_framework (Meson dependency('boost', modules:'unit_test_framework'))
        self.cpp_info.set_property("cmake_file_name", "Boost")
        self.cpp_info.set_property("cmake_target_name", "Boost::boost")
        self.cpp_info.set_property("pkg_config_name", "boost")

        comp = self.cpp_info.components["unit_test_framework"]
        comp.set_property("cmake_target_name", "Boost::unit_test_framework")
        comp.set_property("pkg_config_name", "libboost_unit_test_framework")
        comp.libs = ["boost_unit_test_framework"]
        comp.defines = ["BOOST_TEST_DYN_LINK=0"]
        comp.requires = []

        # Header-only compat component `boost` (Boost::boost) for consumers that
        # only need headers (de-coupled object from unit_test_framework so the
        # library list above is not cleared).
        hdr = self.cpp_info.components["boost"]
        hdr.set_property("cmake_target_name", "Boost::boost")
        hdr.set_property("pkg_config_name", "boost")
        hdr.libs = []
        hdr.defines = []
        hdr.requires = ["unit_test_framework"]
