#!/usr/bin/env python3
"""Conan recipe — maxflow 3.0.5 (CMake, shared C++ graph-cut library).

maxflow (gerddie/maxflow) is Vladimir Kolmogorov and Yuri Boykov's
BK max-flow/min-cut library ("An Experimental Comparison of Min-Cut/
Max-Flow Algorithms for Energy Minimization in Vision", IEEE TPAMI 2004),
packaged upstream with a small CMake build.  The template
Graph<captype,tcaptype,flowtype> is explicitly instantiated inside
maxflow.cpp for int/short/float/double, so consumers only include
<maxflow.h> and link the shared library.

Layout facts that shape this recipe (audited from the 3.0.5 tarball):
  * Upstream hardcodes ADD_LIBRARY(maxflow SHARED maxflow.cpp) — no
    BUILD_SHARED_LIBS option, so this recipe ships the shared library
    exactly as upstream builds it (maxflow is not a system-named library,
    so R26's static rule does not apply).
  * Headers go to include/maxflow-3.0/ (maxflow.h) and
    include/maxflow-3.0/maxflow/ (block.h, graph.h, graph.cpp); the
    consumer include dir is <prefix>/include/maxflow-3.0, NOT include/.
    graph.cpp is installed as a "header" because maxflow.h re-includes it
    when MAXFLOW_INCLUDE_TEMPLATE_IMPLEMENTATION is defined — that macro
    is only used when building the library itself, not by consumers.
  * No CMake package config is generated (the EXPORT MaxFlow set has no
    matching install(EXPORT)), so consumers use the CMakeDeps-generated
    find_package(maxflow) + maxflow::maxflow target from this package.
  * The top-level CMakeLists still advertises MICRO_VERSION 4, so the
    generated maxflow.pc says "Version: 3.0.4" even in the 3.0.5 tag.
    Left as upstream ships it (Debian does the same); see notes.md.
  * The only patch bumps cmake_minimum_required 2.8.5 -> 3.5 for CMake 4
    (knowledge error-pattern E103).
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches,
                               export_conandata_patches, get)


class MaxflowConan(ConanFile):
    name = "maxflow"
    version = "3.0.5"
    description = ("Boykov-Kolmogorov max-flow/min-cut graph cut library "
                   "for energy minimization in vision")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/gerddie/maxflow"
    url = ""  # CI fills this
    # Upstream hardcodes SHARED with no option (see docstring); the generic
    # "library" type would demand a `shared` option in Conan 2, so declare
    # the accurate type instead (repo convention, 161 recipes).
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must be an explicit allow-list
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"maxflow supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # Upstream has zero external dependencies (CMake >= 3.5 and a C++
        # toolchain only); nothing to declare.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # r2/r3 device runs: bare cmake/ctest do not resolve in the runner
        # environment (its PATH lacks the hnp tool dirs).  Inject the known
        # dirs into the build env via the conanbuild script chain (repo
        # convention: nymphcast "PATH probe + hnp fallback"); a profile-level
        # conf or self.conf_info does not reach this node's helpers.
        env = Environment()
        for d in ("/data/service/hnp/cmake.org/cmake_4.1.2/bin",
                  "/data/service/hnp/bin"):
            if os.path.isdir(d):
                env.prepend_path("PATH", d)
        env.vars(self, scope="build").save_script("conanbuild_hnp_path")
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # Treat OHOS as a Linux-like target for CMake (same technique
            # as fast_float / mcfp); the profile supplies the OHOS clang.
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream suite: one ctest entry ("maxflow") driving the
        test-maxflow binary, which executes 3 test functions with 10
        assertions total and exits non-zero on any failure."""
        bin_dir = None
        lib_dir = None
        for root, _dirs, files in os.walk(self.build_folder):
            if bin_dir is None and "CTestTestfile.cmake" in files:
                bin_dir = root
            if lib_dir is None and any(
                    f.startswith("libmaxflow.so") for f in files):
                lib_dir = root
            if bin_dir and lib_dir:
                break
        if bin_dir is None:
            raise ConanInvalidConfiguration(
                "CTestTestfile.cmake not found; upstream tests not runnable")

        # test-maxflow links libmaxflow.so from the build tree and the
        # platform emits no usable RPATH, so make the build dir findable
        # for the ctest run (same technique as the mcfp recipe).
        envobj = Environment()
        if lib_dir:
            envobj.append_path("LD_LIBRARY_PATH", lib_dir)
        with envobj.vars(self).apply():
            self.output.info("=== ctest -N (test discovery) ===")
            self.run("ctest -N", cwd=bin_dir)
            self.output.info("=== ctest --output-on-failure ===")
            # R36: run the ctest driver directly instead of cmake.test()
            # (cmake.test() appends args to the build driver, not ctest).
            rc = self.run("ctest --output-on-failure", cwd=bin_dir,
                          ignore_errors=True)
        self._report_upstream_result(bin_dir, rc)

    def _report_upstream_result(self, bin_dir, rc):
        """Emit the HMBS_UPSTREAM_TEST_RESULT marker from LastTest.log.

        The upstream binary prints exactly one summary line
        "<failures> of <total> test failed", so the log parse is
        deterministic; a non-zero ctest exit code always fails the build.
        """
        executed, failed = 0, 0
        status = "failed"
        reason = ""
        if rc != 0:
            reason = "ctest exited %s" % rc
        log = os.path.join(bin_dir, "Testing", "Temporary", "LastTest.log")
        text = ""
        if os.path.isfile(log):
            with open(log, encoding="utf-8", errors="replace") as f:
                text = f.read()
        m = re.search(r"(\d+) of (\d+) test failed", text)
        if m is not None:
            failed = int(m.group(1))
            executed = int(m.group(2))
            if rc == 0 and failed == 0:
                status = "passed"
        elif rc == 0:
            reason = "summary line not found in LastTest.log"
        marker = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            # 1 ctest entry aggregating 3 upstream test functions.
            "discovered": 3,
            "executed": executed,
            "passed": executed - failed,
            "failed": failed,
            "skipped": 0,
        }
        if reason:
            marker["reason"] = reason
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        if status != "passed":
            raise ConanInvalidConfiguration(
                "upstream maxflow tests failed: %s" % (reason or marker))

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Upstream installs into a versioned include dir:
        #   include/maxflow-3.0/maxflow.h
        #   include/maxflow-3.0/maxflow/{block.h, graph.h, graph.cpp}
        # maxflow.h does #include <maxflow/block.h>, so the consumer
        # include dir is include/maxflow-3.0 (parent of the subtree).
        self.cpp_info.includedirs = [os.path.join("include", "maxflow-3.0")]
        self.cpp_info.libs = ["maxflow"]
