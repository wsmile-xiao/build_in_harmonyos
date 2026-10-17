#!/usr/bin/env python3
"""Consumer and negative tests for packaged MLton."""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class MltonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("交叉构建场景不运行目标程序")
            return
        package = self.dependencies["mlton"].package_folder
        mlton = os.path.join(package, "bin", "mlton")
        source = os.path.join(self.source_folder, "hello.sml")
        bad = os.path.join(self.source_folder, "invalid.sml")
        output = os.path.join(self.build_folder, "mlton-consumer")
        wrapper = os.path.join(self.source_folder, "run_consumer_tests.sh")
        self.run(f'/usr/bin/sh "{wrapper}" "{mlton}" "{source}" "{output}"',
                 env="conanrun")
        self.output.info("CONSUMER_TEST_MARKER: packaged mlton compile/run PASS")
        result = subprocess.run(
            [mlton, "-codegen", "c", "-output", output + "-bad", bad],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=os.environ.copy())
        self.output.info(result.stdout)
        if result.returncode == 0:
            raise ConanException("negative syntax test unexpectedly succeeded")
        self.output.info("NEGATIVE_TEST_MARKER: invalid SML rejected PASS")
        required = [
            "bin/mlton", "bin/mllex", "bin/mlyacc", "bin/mlprof",
            "lib/mlton/mlton-compile", "lib/mlton/include/platform.h",
        ]
        missing = [item for item in required if not os.path.exists(os.path.join(package, item))]
        if missing:
            raise ConanException(f"package validation missing files: {missing}")
        self.output.info("PACKAGE_VALIDATION_MARKER: compiler/tool/runtime tree PASS")
