#!/usr/bin/env python3
"""Conan test_package — rhonabwy 1.1.13 (consumer view).

Real API usage (R34): the consumer program links the exported
Rhonabwy::Rhonabwy target and runs a complete compact-JWS round trip against
the installed package - import an "oct" JWK, sign a payload with HS256, parse
the token back, verify the signature and finally check that a tampered token
is rejected (the assertion count is read back from the program's own
"# N assertions, M failures" line, see test_rhonabwy.c).

Emits the HMBS_TEST_PACKAGE_RESULT hard-gate marker with the real consumer
assertion count. The binary is run with env="conanrun" plus an explicit
LD_LIBRARY_PATH/LD_PRELOAD: on OHOS the loader ignores LD_LIBRARY_PATH while
resolving the shared dependency chain of librhonabwy.so and reports
"Error relocating .../librhonabwy.so: gnutls_strerror: symbol not found"
([stale_runtime_library] diagnostic), so the freshly built dependency lib dirs
are prepended and the current libgnutls.so.30 is preloaded - the same
constraint the ulfius 2.7.15 test package in this repository handles.
"""
import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class RhonabwyTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # include/rhonabwy.h is a "fat" public header: it includes <jansson.h>,
        # <gnutls/gnutls.h> and <nettle/version.h> unconditionally, so a consumer
        # compiling against it needs those include directories. CMakeDeps only
        # writes usable data files (include dirs, libs, targets) for the
        # requirements that are DIRECT in the generating context - for a purely
        # transitive one it emits e.g. `set(jansson_INCLUDE_DIRS_RELEASE )` and the
        # exported Rhonabwy target then carries no include path for it. Declaring
        # them here (same pins as the tested recipe) makes their usage
        # requirements part of the consumer graph, exactly like an application
        # linking against rhonabwy.h has to do.
        self.requires("jansson/2.15.1.1")
        self.requires("gnutls/3.8.10")
        self.requires("nettle/3.10.2.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        exe = os.path.join(self.cpp.build.bindirs[0], "test_rhonabwy")

        # Every dependency lib dir of the graph (also the transitive ones that
        # VirtualRunEnv leaves out) plus the fresh libgnutls.so.30 for LD_PRELOAD.
        dep_lib_dirs = []
        for dep in self.dependencies.values():
            folder = getattr(dep, "package_folder", None)
            if folder:
                libdir = os.path.join(folder, "lib")
                if os.path.isdir(libdir):
                    dep_lib_dirs.append(libdir)

        preload = None
        try:
            gnutls_folder = self.dependencies["gnutls"].package_folder
        except Exception:
            gnutls_folder = None
        if gnutls_folder:
            for name in ("libgnutls.so.30", "libgnutls.so"):
                candidate = os.path.join(gnutls_folder, "lib", name)
                if os.path.exists(candidate):
                    preload = candidate
                    break

        ld_library_path = ":".join(dep_lib_dirs + [os.environ.get("LD_LIBRARY_PATH", "")])
        env_prefix = "export LD_LIBRARY_PATH={}; ".format(shlex.quote(ld_library_path))
        if preload:
            env_prefix += "export LD_PRELOAD={}; ".format(shlex.quote(preload))
        # The test program prints "# <n> assertions, <m> failures" as its last
        # line (see the counter in test_rhonabwy.c); parse it instead of
        # hardcoding the count, so the hard-gate marker always reports what the
        # binary really executed.
        run_log = os.path.join(self.build_folder, "test_package_run.log")
        command = (env_prefix + shlex.quote(exe) + " > " + shlex.quote(run_log)
                   + " 2>&1")
        result = {"executed": True, "passed": False, "command": command,
                  "discovered": 0, "passedCount": 0}
        try:
            self.run(command, env="conanrun")
            result["passed"] = True
        finally:
            assertions = failures = None
            if os.path.exists(run_log):
                with open(run_log, encoding="utf-8", errors="replace") as fh:
                    match = re.search(r"#\s*(\d+)\s+assertions,\s*(\d+)\s+failures",
                                      fh.read())
                if match:
                    assertions, failures = int(match.group(1)), int(match.group(2))
            if assertions is None:
                assertions = failures = 0
            result["discovered"] = assertions
            result["passedCount"] = assertions - failures if result["passed"] else 0
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
        if not result["discovered"]:
            # Never let a silent parse failure downgrade the hard gate to a
            # zero-valued marker: the binary exited 0 and must have reported
            # its own assertion count.
            raise ConanException(
                "the consumer test program succeeded but did not report its "
                "assertion count ('# N assertions, M failures' missing in %s)"
                % run_log)
