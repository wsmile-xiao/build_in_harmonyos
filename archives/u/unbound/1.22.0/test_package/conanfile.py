#!/usr/bin/env python3
"""Conan test_package — unbound 1.22.0 (L1 official test).

Substantive verification (R34):
  1. Compiles test.c against libunbound via unbound::unbound and runs it
     (ub_ctx_create / ub_ctx_set_option / ub_ctx_get_option / ub_ctx_delete)
     under the conanrun environment (so dynamic deps libevent/openssl/expat
     are on LD_LIBRARY_PATH).
  2. Executes the packaged unbound-checkconf binary to prove the shipped
     executables run.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class UnboundTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        # Run the API test binary under the conanrun env so that dynamic
        # dependencies (libevent-2.1.so.7, libssl.so.3, libexpat.so) resolve.
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_unbound")
        self.run(f'"{test_bin}"', env="conanrun")

        # Verify the packaged unbound-checkconf executable runs and validates a
        # real config. NOTE: `unbound-checkconf -h` prints usage but exits 1 by
        # upstream design, so we validate a minimal config instead (exits 0).
        pkg = self.dependencies["unbound"].package_folder
        checkconf = os.path.join(pkg, "bin", "unbound-checkconf")
        conf = os.path.join(self.build_folder, "unbound-test.conf")
        conf_body = (
            "server:\n"
            "    directory: %s\n"
            '    pidfile: "%s/unbound-test.pid"\n'
            '    logfile: "%s/unbound-test.log"\n'
            '    username: ""\n'
            '    chroot: ""\n'
        ) % (self.build_folder, self.build_folder, self.build_folder)
        with open(conf, "w", encoding="utf-8") as fh:
            fh.write(conf_body)
        self.run(f'"{checkconf}" -o logfile "{conf}"', env="conanrun")
