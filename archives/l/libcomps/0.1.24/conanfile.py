#!/usr/bin/env python3
"""Conan recipe for libcomps 0.1.24 — RPM/DNF comps XML library (CMake, C + Python 3).

libcomps is the library behind the RPM/DNF *comps* (package group) XML format:
a C library (``libcomps.so``/``libcomps.a``, pkg-config ``libcomps``) plus the
Python 3 binding that upstream also publishes as the ``libcomps`` wheel.

The CMake project root of the 0.1.24 tarball is the ``libcomps/`` subdirectory
(the tarball top level only carries ``version.cmake``, the RPM spec and the
scikit-build metadata), so the recipe configures with
``build_script_folder="libcomps"`` — the same entry point the upstream RPM spec
uses (``%cmake ../libcomps/``).  ``ENABLE_TESTS=ON`` is upstream's default and
the recipe runs the complete upstream suite (``test`` target = ``ctest`` +
``pytest``) inside ``build()``.
"""

import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibcompsConan(ConanFile):
    name = "libcomps"
    version = "0.1.24"
    description = (
        "libcomps is an alternative to yum.comps written in C: it parses, "
        "validates, queries, merges and serializes RPM/DNF comps (package "
        "group) XML documents, and ships a Python 3 binding"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/rpm-software-management/libcomps"
    url = "https://github.com/rpm-software-management/libcomps"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        # libcomps' installed headers include <libxml/encoding.h>,
        # <libxml/parser.h> and <expat.h>, so both dependencies have to keep
        # propagating their headers to consumers of this package.
        self.requires("libxml2/2.15.3.1", transitive_headers=True)
        self.requires("expat/2.8.2.1", transitive_headers=True)
        # The Python binding is built unconditionally by upstream's
        # src/CMakeLists.txt (add_subdirectory(python)) and links libpython,
        # so Python is a host requirement of this package.
        self.requires("python/3.12.9")

    def build_requirements(self):
        # Only the upstream Check-based suite needs libcheck; it is not part of
        # the installed libcomps link interface.
        self.test_requires("check/0.15.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dependency(self, name):
        for dependencies in (
            self.dependencies.test,
            self.dependencies.host,
            self.dependencies.build,
        ):
            try:
                return dependencies[name]
            except KeyError:
                continue
        return None

    def generate(self):
        python = self._dependency("python")
        check = self._dependency("check")
        if python is None:
            raise ConanException("python dependency is missing from the graph")

        py_include = os.path.dirname(
            self._first_match(
                os.path.join(python.package_folder, "include", "python*", "Python.h"),
                "Python.h",
            )
        )
        py_library = self._first_match(
            os.path.join(python.package_folder, "lib", "libpython3*.so"),
            "libpython shared library",
        )

        # Generate the Conan CMake config files for the dependencies.  Without
        # them, and because Conan sets CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON,
        # find_package() resolves to whatever the build machine exposes (on the
        # HarmonyOS device that is the host ~/.harmonybrew tree) instead of the
        # packages in the graph.
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_LIBCOMPS_SHARED"] = bool(self.options.shared)
        tc.variables["ENABLE_DEVELOPMENT"] = True
        # The documentation targets need Doxygen, which is not part of the
        # OHOS toolchain and is not part of the installed package.
        tc.variables["ENABLE_DOCS"] = False
        tc.variables["ENABLE_TESTS"] = True

        # Upstream reads the *legacy variable* spellings of the XML/zlib
        # dependencies (LIBXML2_INCLUDE_DIR, LIBXML2_LIBRARIES, EXPAT_LIBRARY,
        # ZLIB_INCLUDE_DIRS, ...) instead of the imported targets that the
        # generated Conan config files define.  Pin every variable the project
        # consumes to the Conan package folders so the build cannot silently
        # pick up a host library and stays reproducible on a clean worker.
        for name, variables in (
            (
                "libxml2",
                {
                    "LIBXML2_INCLUDE_DIR": ("include", "libxml2"),
                    "LIBXML2_LIBRARY": ("lib", "libxml2.so*"),
                    "LIBXML2_LIBRARIES": ("lib", "libxml2.so*"),
                },
            ),
            (
                "expat",
                {
                    "EXPAT_INCLUDE_DIR": ("include",),
                    "EXPAT_LIBRARY": ("lib", "libexpat.so*"),
                    "EXPAT_LIBRARIES": ("lib", "libexpat.so*"),
                },
            ),
            (
                "zlib",
                {
                    "ZLIB_INCLUDE_DIRS": ("include",),
                    "ZLIB_LIBRARY": ("lib", "libz.*"),
                    "ZLIB_LIBRARIES": ("lib", "libz.*"),
                },
            ),
        ):
            dependency = self._dependency(name)
            if dependency is None:
                raise ConanException(f"{name} dependency is missing from the graph")
            for variable, parts in variables.items():
                target = os.path.join(dependency.package_folder, *parts)
                if "*" in parts[-1]:
                    tc.variables[variable] = self._first_match(target, variable)
                elif os.path.isdir(target):
                    tc.variables[variable] = target
                else:
                    raise ConanException(f"unable to locate {variable}: {target}")

        # CHECK_INCLUDE_DIR is never assigned upstream, and
        # FindPythonInterp/FindPythonLibs cannot guess a Conan-provided
        # interpreter.  Supply them explicitly instead of patching find logic.
        tc.variables["PYTHON_EXECUTABLE"] = os.path.join(
            python.package_folder, "bin", "python3"
        )
        tc.variables["PYTHON_INCLUDE_DIR"] = py_include
        tc.variables["PYTHON_LIBRARY"] = py_library
        tc.variables["PYTHON_LIBRARIES"] = py_library
        # The pure-python half of the binding must land inside the Conan
        # package instead of the interpreter's absolute sitearch directory.
        tc.variables["PYTHON_INSTALL_DIR"] = os.path.join(
            self.package_folder, "python", "site-packages"
        )
        if check is not None:
            tc.variables["CHECK_INCLUDE_DIR"] = os.path.join(
                check.package_folder, "include"
            )
            tc.variables["CHECK_LIBRARY"] = os.path.join(
                check.package_folder, "lib", "libcheck.so"
            )
        tc.generate()

    def _first_match(self, pattern, description):
        matches = sorted(glob.glob(pattern))
        if not matches:
            raise ConanException(f"unable to locate {description}: {pattern}")
        return matches[0]

    def _runtime_libdirs(self):
        libdirs = []
        for dependencies in (self.dependencies.host, self.dependencies.test):
            for _, dependency in dependencies.items():
                libdir = os.path.join(dependency.package_folder, "lib")
                if os.path.isdir(libdir):
                    libdirs.append(libdir)
        return libdirs

    def _environment(self, for_tests=False):
        env = Environment()
        # libpython, libcheck, libexpat and libxml2 are shared libraries that
        # live in Conan package folders; the configure probes and the test
        # binaries both have to be able to load them.
        for libdir in self._runtime_libdirs():
            env.prepend_path("LD_LIBRARY_PATH", libdir)
        if str(self.settings.os) == "OHOS":
            # /tmp is read-only on the target.
            test_tmp = os.path.join(self.build_folder, "tmp")
            os.makedirs(test_tmp, exist_ok=True)
            env.define("TMPDIR", test_tmp)
            env.define("TMP", test_tmp)
            env.define("TEMP", test_tmp)
            if for_tests:
                # Check's default forked runner needs IPC temporary files that
                # HMDFS refuses to create; in-process mode keeps every test.
                env.define("CK_FORK", "no")
        return env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._environment().vars(self).apply():
            cmake.configure(build_script_folder="libcomps")
            cmake.build()
        with self._environment(for_tests=True).vars(self).apply():
            # Upstream "test" target == "ctest" (test_comps_run + test_parse_run).
            cmake.build(target="test")
            # The Python binding is part of this package, but upstream 0.1.24
            # never wires "pytest" to "pytest_run" (libcomps/CMakeLists.txt
            # declares `add_custom_target(pytest)` with no dependencies), so the
            # "test" target alone would leave the shipped binding unverified.
            # Run the registered target explicitly: it executes __test.py,
            # test_libcomps.py and test_merge_comps.py against the module that
            # was just built.
            cmake.build(target="pytest_run")

    def package(self):
        cmake = CMake(self)
        with self._environment().vars(self).apply():
            cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libcomps")
        self.cpp_info.set_property("cmake_target_name", "libcomps::libcomps")
        self.cpp_info.set_property("pkg_config_name", "libcomps")
        self.cpp_info.libs = ["comps"]
