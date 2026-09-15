#!/usr/bin/env python3
"""Consumer test for the packaged debfoster executable."""
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class DebfosterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder=".")

    def test(self):
        if not can_run(self):
            self.output.warning("Skipping execution because the target cannot run here")
            return

        # The packaged tool needs a shell to drive it: test.sh builds dpkg
        # status fixtures and compares exact stdout.  /bin/sh on OHOS is toybox
        # ash, so the device bash has to be used.
        #
        # CONFIG_SHELL is read with `or` rather than as a get() default so that
        # an empty value also falls through to the device bash.  There must be
        # no intermediate os.environ["SHELL"] link: CONFIG_SHELL is *not*
        # exported into test()'s environment (measured: it is unset there),
        # while SHELL is "/bin/sh", so such a link would silently downgrade the
        # interpreter to toybox ash and contradict the intent of this comment
        # (and test_package/MANIFEST.yml).  Measured in the accepted round:
        #   RUN: /data/service/hnp/bin/bash .../test_package/test.sh
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f"{shlex.quote(bash)} {shlex.quote(script)}", env="conanrun")
