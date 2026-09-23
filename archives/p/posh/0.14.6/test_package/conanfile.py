import os

from conan import ConanFile


class PoshTestConan(ConanFile):
    """test_package for posh — R34 smoke suite (consumer perspective).

    Exercising the installed `posh` binary for real: POSIX shell
    semantics (arithmetic/variable expansion, pipelines, redirections,
    exit-code propagation, functions, if/case/for control flow) via
    `posh -c`, script-file mode (both `posh script.sh` and a `#!/usr/bin/env
    posh` executable), and the $POSH_VERSION assertion (see T1 for the
    upstream forgot-to-bump quirk).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute the test suite
        # reliably; wrap with bash (aa3d/brender/poke test_package
        # precedent).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run('"{}" test.sh'.format(bash), env="conanrun")
