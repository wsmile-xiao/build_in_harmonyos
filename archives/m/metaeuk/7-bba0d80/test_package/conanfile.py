"""Consumer test package for metaeuk 7-bba0d80.

Runs the packaged metaeuk binary (application package) through real
behavior assertions implemented in consumer.cpp: bare-invocation version
banner, help exit code, argument validation, an end-to-end easy-predict
workflow (product-name check only; synthetic data yields 0-byte outputs),
and a self-contained createdb round-trip asserting non-empty db/db_h.
"""

from os.path import join

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class MetaeukTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the consumer unconditionally. A silent `if can_run(self)` skip
        # would report success without executing a single assertion (rc=0),
        # which defeats both the R34 destructive negative test (CI L1e, which
        # removes the package artifacts and re-runs `conan test`) and CI in
        # general. This package is always built natively - the real device and
        # the CI worker both pass the host profile as the build profile - so
        # there is no legitimate cross-build scenario to short-circuit here.
        self.run(
            join(self.cpp.build.bindirs[0], "metaeuk_consumer"),
            cwd=self.build_folder,
            env="conanrun",
        )
