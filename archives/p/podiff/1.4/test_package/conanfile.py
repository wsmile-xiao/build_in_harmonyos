#!/usr/bin/env python3
"""test_package for podiff — PO file comparison tool (R34 substantive test).

Invokes the packaged podiff binary through test.sh, which asserts the
documented exit-code semantics:
  0 = two PO files are equivalent
  1 = files differ (works after the ignore_rc upstream fix)
  2 = invalid command line option (man page RETURN VALUE)
  3 = PO syntax/parse error (podiff.l: yyparse() failure -> exit(3))
"""
import os

from conan import ConanFile


class PodiffTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the packaged binary; test.sh hard-fails if it is missing
        # (L1e destructive proof: a package without the binary must FAIL).
        podiff = os.path.join(self.dependencies["podiff"].package_folder,
                              "bin", "podiff")
        # OHOS: use bash to wrap binary execution (mksh may be unreliable)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} test.sh "{podiff}"', env="conanrun")
