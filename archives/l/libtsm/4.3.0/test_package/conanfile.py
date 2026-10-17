#!/usr/bin/env python3
"""test_package for libtsm/4.3.0 — real consumer of the installed library.

Builds ``test_libtsm.c`` against the packaged ``libtsm`` (CMakeDeps +
CMakeToolchain), runs the binary and validates its self-reported check count,
so a truncated or empty run cannot pass silently.

The upstream meson test suite compiles the library sources directly into each
test binary (``declare_dependency(..., sources: libtsm_srcs)``), therefore it
never loads the shipped ``libtsm.so``. This consumer is linked against the
packaged artifact and covers the public API of what is actually delivered.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

# check count expected from test_libtsm.c; a smaller number means the consumer
# did not execute completely and must not be reported as a pass
EXPECTED_CHECKS = 47


class LibtsmTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._check_pkg_config_artifact()

        if not can_run(self):
            self.output.warning("libtsm binaries cannot run on this machine "
                                "(os=%s); consumer execution skipped"
                                % self.settings.os)
            return

        exe = os.path.join(self.cpp.build.bindirs[0], "test_libtsm")
        out_file = os.path.join(self.build_folder, "test_libtsm.out")
        self.run('"%s" > "%s" 2>&1' % (exe, out_file), env="conanrun")

        out = open(out_file, encoding="utf-8", errors="replace").read()
        self.output.info("consumer output:\n%s" % out)

        match = re.search(r"^CHECKS: (\d+)/(\d+) passed$", out, re.M)
        if not match:
            raise ConanException("test_libtsm printed no 'CHECKS: n/n passed' "
                                 "summary line")
        passed, total = int(match.group(1)), int(match.group(2))
        if total != EXPECTED_CHECKS:
            raise ConanException("consumer executed %d checks, expected %d "
                                 "(incomplete run)" % (total, EXPECTED_CHECKS))
        if passed != total:
            raise ConanException("consumer checks failed: %d/%d passed"
                                 % (passed, total))
        if "RESULT: PASS" not in out:
            raise ConanException("consumer printed no 'RESULT: PASS' line")

    def _check_pkg_config_artifact(self):
        """The package must ship the meson generated pkg-config file."""
        pkg_folder = self.dependencies["libtsm"].package_folder
        pc_file = os.path.join(pkg_folder, "lib", "pkgconfig", "libtsm.pc")
        if not os.path.isfile(pc_file):
            raise ConanException("libtsm.pc missing from the package: %s"
                                 % pc_file)
        content = open(pc_file, encoding="utf-8", errors="replace").read()
        if "Version: 4.3.0" not in content:
            raise ConanException("libtsm.pc does not declare version 4.3.0:\n%s"
                                 % content)
        if "-ltsm" not in content:
            raise ConanException("libtsm.pc does not link -ltsm:\n%s" % content)
        self.output.info("packaged pkg-config file:\n%s" % content)
