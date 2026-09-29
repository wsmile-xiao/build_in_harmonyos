import os

from conan import ConanFile


class LucyTestConan(ConanFile):
    """Consumer-view test for the lucy CLI (test_package layer).

    lucy is a stand-alone command line tool, so the test_package does not link
    a library: it resolves `lucy` from the installed package (conanrun PATH) and
    runs the OHOS consumer case end to end — real trimming on a real read set
    followed by the upstream zapping.awk post-processing step.
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so a shell
        # wrapper is used (same idiom as the other OHOS packages in this repo).
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{shell} consumer_case.sh', env="conanrun")
