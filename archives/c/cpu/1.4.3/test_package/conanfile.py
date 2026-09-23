#!/usr/bin/env python3
"""Conan L1 test_package for cpu 1.4.3 (HarmonyOS PC / OHOS aarch64).

Upstream 1.4.3 ships no test suite: the top-level `check' target has no TESTS
entries (make check is a no-op) and doc/test.ldif is LDAP fixture data, not an
automated test.  The adaptation tests carried here are therefore:

  1. CLI contract   -- `cpu --version' and `cpu --help' run and report 1.4.3 /
                       the documented commands.
  2. Plugin loading -- `cpu -M ldap' dlopen()s libcpu_ldap.so and reaches the
                       libldap call.  This is the platform-critical property of
                       the port: the method plugin must be a shared module with
                       correct DT_NEEDED entries (libcputil.so.0, libldap.so.2),
                       which is what the libtool platform-table / Makefile
                       patches repair.
  3. Consumer test  -- consumer.c is linked against the package's libcputil.so
                       and exercises its public helper API (Strdup/Free,
                       md5_buffer, cgetpwent) with known-answer assertions.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class CpuTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        env = Environment()
        for _, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            for bindir in dep.cpp_info.bindirs:
                env.prepend_path("PATH", os.path.join(dep.package_folder, bindir))
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, libdir))
        name = self.tested_reference_str.split("/")[0]
        env.define("CPU_TEST_ROOT", self.dependencies[name].package_folder)
        env.vars(self, scope="run").save_script("conanrun")

    def test(self):
        if not can_run(self):
            return
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries: run the test
        # through bash (CONFIG_SHELL is provided by the CI profile).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # conan's self.run() is unusable here: its runner dies with SIGSEGV on
        # this platform, so the script is started directly through subprocess.
        dep = self.dependencies["cpu"]

        # cpp_info dirs are relative to the package folder they belong to.
        def dirs_of(ref, attr):
            out = []
            for pkg in [ref] + list(ref.dependencies.values()):
                if not pkg.package_folder:
                    continue
                out += [os.path.join(pkg.package_folder, d)
                        for d in getattr(pkg.cpp_info, attr)]
            return out

        env = os.environ.copy()
        env["CPU_TEST_ROOT"] = dep.package_folder
        for var, paths in (("LD_LIBRARY_PATH", dirs_of(dep, "libdirs")),
                           ("PATH", dirs_of(dep, "bindirs"))):
            # conanrun already exports the package dirs; prepend ours and drop
            # empty entries (an empty element means the current directory).
            env[var] = os.pathsep.join([p for p in paths + [env.get(var, "")] if p])
        subprocess.check_call([bash, "test.sh"],
                              cwd=os.path.dirname(os.path.realpath(__file__)), env=env)
