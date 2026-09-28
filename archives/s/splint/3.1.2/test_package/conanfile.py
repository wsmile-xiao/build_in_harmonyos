#!/usr/bin/env python3
"""test_package for splint/3.1.2 — drives the installed CLI as a consumer would.

`test.sh` is executed through bash because the OHOS default shell (mksh) cannot
execute ELF binaries (2048.c precedent).  `env="conanrun"` publishes the package's
runenv_info, i.e. LARCH_PATH pointing at the packaged .lcd model library.
"""

import os

from conan import ConanFile


class SplintTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        splint = os.path.join(dep.package_folder, "bin", "splint")
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries -> wrap in bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # splint needs a writable directory for its pre-processor scratch files and
        # /tmp is a read-only erofs mount on OHOS (E002); 0003-src-context.c.patch
        # makes the POSIX build honour TMPDIR.
        tmpdir = os.path.join(self.build_folder, "splint-tmpdir")
        os.makedirs(tmpdir, exist_ok=True)
        self.run(
            'TMPDIR="{}" {} test.sh "{}"'.format(tmpdir, bash, splint), env="conanrun"
        )
