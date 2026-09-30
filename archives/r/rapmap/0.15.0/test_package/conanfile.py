import os

from conan import ConanFile


class RapmapTestConan(ConanFile):
    """test_package for rapmap -- consumer test for an executable-only package.

    Runs test.sh, which drives the packaged ``rapmap`` binary through a real
    quasiindex + quasimap round trip on a synthesised transcriptome.

    can_run() gating is deliberately not used here: the OHOS profile pins
    ``tools.build.cross_building:can_run=False``, which would silently skip the
    execution and produce a false green build.  ``/system/bin/sh`` on OHOS
    (mksh) cannot execute ELF binaries, so the script is invoked through bash.
    """
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run('"%s" test.sh' % bash, env="conanrun")
