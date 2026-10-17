#!/usr/bin/env python3
"""Conan test_package for libbpp-popgen 2.4.1.

Consumer-side verification of the *installed* package: the public Bio++
PopGen API is exercised from a separate CMake project that only sees the
packaged headers, archives and CMake package files.

Why the archives are pinned by absolute path (see CMakeLists.txt): upstream
installs a static+shared pair, and resolving the shared object would introduce
a runtime loader dependency. Linking `libbpp-popgen.a` + `libbpp-seq.a` +
`libbpp-core.a` gives a fully static consumer, so the test binary runs wherever
the target can execute binaries (including a cross-build host with a working
aarch64 loader) and never depends on `LD_LIBRARY_PATH`.

The test itself is registered with ctest so `ctest --output-on-failure`
provides the execution evidence required by the CI test gate.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibbppPopgenTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        popgen_folder = self.dependencies["libbpp-popgen"].package_folder
        seq_folder = self.dependencies["libbpp-seq"].package_folder
        self.output.info("libbpp-popgen package folder: %s" % popgen_folder)
        self.output.info("libbpp-seq    package folder: %s" % seq_folder)
        tc = CMakeToolchain(self)
        tc.variables["LIBBPP_POPGEN_PACKAGE_FOLDER"] = popgen_folder.replace("\\", "/")
        tc.variables["LIBBPP_SEQ_PACKAGE_FOLDER"] = seq_folder.replace("\\", "/")
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _ctest_bin(self):
        """Resolve ctest without relying on the inherited shell PATH.

        Conan's own runner picks up the generated environment, but the CI
        worker image does not always expose cmake/ctest on the base PATH
        (libbpp-seq precedent: FileNotFoundError 'cmake' on PR #10479), so
        fall back to the HNP tool directories shared by CI and preflight.
        """
        sibling = os.path.join(
            os.path.dirname(self.conf.get("tools.cmake:cmake_program", default="") or ""),
            "ctest",
        )
        found = shutil.which("ctest")
        if found:
            return found
        if os.path.isfile(sibling):
            return sibling
        for cand in (
            "/data/service/hnp/bin/ctest",
            "/storage/Users/currentUser/usr/local/bin/ctest",
            "/usr/local/bin/ctest",
            "/usr/bin/ctest",
        ):
            if os.path.isfile(cand):
                return cand
        return "ctest"

    def test(self):
        if not can_run(self):
            self.output.info(
                "cross-building: consumer compiled and linked against the static "
                "archives; execution deferred to a host able to run target binaries"
            )
            return
        ctest_bin = self._ctest_bin()
        self.output.info("ctest binary: %s" % ctest_bin)
        test_home = os.path.join(self.build_folder, "test-home")
        os.makedirs(test_home, exist_ok=True)
        env = Environment()
        env.define("HOME", test_home)
        with env.vars(self).apply():
            # env="conanrun" applies the aggregated runtime environment (the
            # consumer is a native binary on the CI worker, where the C++
            # runtime directories are only reachable through that env).
            self.run(f'"{ctest_bin}" --output-on-failure', cwd=self.build_folder, env="conanrun")
