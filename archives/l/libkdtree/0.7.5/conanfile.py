#!/usr/bin/env python3
"""Conan recipe — libkdtree++ 0.7.5 (header-only C++ template kd-tree library).

Upstream : https://github.com/nvmd/libkdtree  (tag v0.7.5)
License  : Artistic-2.0 (COPYING in the source tree root)

libkdtree++ is an STL-like, template-only k-dimensional sorting container:
the whole library lives in the six headers under ``kdtree++/`` and nothing is
compiled into a library artifact.  The recipe is therefore a ``header-library``
package:

  * source()  — official GitHub tag tarball (R39).
  * build()   — compiles the upstream example programs (``examples/*.cpp``) with
                the OHOS clang toolchain and *runs* them; they are the upstream
                test entry points (there is no ctest/pytest registration), and
                they abort on failure because they are assert-based.
  * package() — installs ``kdtree++/*.hpp`` under ``include/kdtree++/``.

Header layout note: the upstream CMake install rule flattens the headers into
``include/`` (``install(FILES ${KDTREE_HEADERS} DESTINATION .../include)``),
which would break ``#include <kdtree++/...>``.  The upstream autotools rule
uses the correct ``kdtree++/`` prefix, and that is the layout packaged here.
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibkdtreeConan(ConanFile):
    name = "libkdtree"
    version = "0.7.5"
    description = ("libkdtree++ - an STL-like C++ template container "
                   "implementation of k-dimensional space sorting using a kd-tree")
    license = "Artistic-2.0"
    homepage = "https://github.com/nvmd/libkdtree"
    url = "https://github.com/nvmd/libkdtree"  # CI fills this
    topics = ("kd-tree", "header-only", "template", "container", "c++")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    # Upstream test entry points: examples/*.cpp, built as executables by the
    # upstream CMakeLists.  There is no ``tests/`` directory and no ctest or
    # pytest registration upstream.
    _upstream_tests = ("test_kdtree", "test_hayne", "test_find_within_range")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The SWIG based python bindings are optional upstream and are not part
        # of the packaged interface; disable them so no SWIG/Python is pulled in.
        tc.variables["BUILD_PYTHON_BINDINGS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _find_program(self, name):
        for candidate in (os.path.join(self.build_folder, "examples", name),
                          os.path.join(self.build_folder, name)):
            if os.path.isfile(candidate):
                return candidate
        return None

    def _run_upstream_tests(self):
        """Build-time execution of the upstream example/test programs (R51)."""
        executed = 0
        passed = 0
        failures = []
        for name in self._upstream_tests:
            program = self._find_program(name)
            if program is None:
                failures.append("%s: binary not built" % name)
                continue
            executed += 1
            proc = subprocess.run([program], cwd=self.build_folder,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=1800)
            log_path = os.path.join(self.build_folder, "upstream-%s.log" % name)
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(proc.stdout or "")
            if proc.returncode == 0:
                passed += 1
            else:
                failures.append("%s: exit %d" % (name, proc.returncode))

        marker = {
            "status": "passed" if not failures else "failed",
            "framework": "upstream examples (assert-based)",
            "command": "examples/<program>",
            "discovered": len(self._upstream_tests),
            "executed": executed,
            "passed": passed,
            "failed": len(failures),
            "failures": failures,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(marker, ensure_ascii=False))
        if failures:
            raise ConanException("upstream test failure: " + "; ".join(failures))

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "kdtree++"),
             dst=os.path.join(self.package_folder, "include", "kdtree++"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libkdtree")
        self.cpp_info.set_property("cmake_target_name", "libkdtree::libkdtree")
