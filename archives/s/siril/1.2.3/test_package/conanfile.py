#!/usr/bin/env python3
"""Conan test_package for siril 1.2.3.

siril is an application (package_type=application), not a library, so it
exposes no CMake/Conan targets for consumers.  This test locates the siril
binaries in the installed package and, when the target can run on the build
host, executes the headless `siril-cli` to verify it is a working executable
(R34: real use of the packaged product, not a print-only stub).  It also
re-emits the HMBS_UPSTREAM_TEST_RESULT marker carried from build() (the
upstream unit tests already ran during build; cache hits never re-run
build(), so the marker must be re-printed here for the HMBS gate).
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class SirilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv provides the conanrun environment (LD_LIBRARY_PATH etc.)
    # needed to launch the packaged binaries against conan-managed shared
    # dependencies.
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The application ships siril (GTK GUI) and siril-cli (headless CLI).
        bindir = os.path.join(self.dependencies["siril"].package_folder, "bin")
        siril_bin = os.path.join(bindir, "siril")
        siril_cli_bin = os.path.join(bindir, "siril-cli")

        if not os.path.isfile(siril_bin) or not os.path.isfile(siril_cli_bin):
            raise Exception(f"Missing siril binaries in {bindir}: "
                            f"siril={os.path.isfile(siril_bin)} "
                            f"siril-cli={os.path.isfile(siril_cli_bin)}")
        self.output.info(f"siril binary present: {siril_bin}")
        self.output.info(f"siril-cli binary present: {siril_cli_bin}")

        # Headless functional check: run test.sh (R34 real consumer test) —
        # it executes the packaged siril-cli with the absolute path and
        # asserts rc==0 plus version output "siril 1.2.3".
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            rc = self.run(f'{bash} test.sh "{siril_cli_bin}"',
                          env="conanrun", ignore_errors=True)
            if rc != 0:
                raise Exception("siril-cli consumer test failed "
                                f"(rc={rc})")
            self.output.info("siril-cli ran OK (headless check passed)")

        # Re-emit the HMBS_UPSTREAM_TEST_RESULT marker from the packaged build
        # evidence (res/upstream_test_result.json).  build() already ran and
        # gated on the 11 upstream unit tests; cache hits need the marker here.
        res_path = os.path.join(self.dependencies["siril"].package_folder,
                                "res", "upstream_test_result.json")
        if not os.path.isfile(res_path):
            raise Exception(f"Missing packaged upstream test result: {res_path}")
        with open(res_path, encoding="utf-8") as fh:
            result = json.load(fh)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        if result.get("status") != "passed":
            raise Exception("Upstream test result in package is not 'passed': "
                            f"{json.dumps(result)}")
