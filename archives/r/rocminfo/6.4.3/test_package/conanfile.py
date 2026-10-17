#!/usr/bin/env python3
"""Test package — rocminfo 6.4.3 on OpenHarmony PC (consumer view).

Conan L1 test. It verifies the packaged deliverable the way a real consumer
would: the installed `rocm_agent_enumerator` command is located on PATH (put
there by the package's `package_info` runenv) and executed as a command —
**not** as `python3 <path-to-script>`.

Why that detail matters (AI review, rule RV-34 / R40): driving the script with
an explicit interpreter makes the host interpreter the thing actually under
test, whereas a package that ships no usable command would still "pass". The
upstream consumer contract is that the script is an *installed program*
(`CMakeLists.txt:180` → `install(PROGRAMS ... DESTINATION ${CMAKE_INSTALL_BINDIR})`),
so this test resolves the command on PATH and runs it directly.

The real assertions live in `test.sh` (run inside the `conanrun` environment so
PATH contains the package `bin/`). Keeping them in a shell driver matches the
repository's `templates/test_package-executable/` layout and makes the test
runnable verbatim on the device as well.
"""
import os

from conan import ConanFile


class RocminfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS PC: /system/bin/sh (mksh) cannot execute ELF binaries directly;
        # the hnp bash is used to drive the consumer script, same as the
        # repository's executable-package test template.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.exists(bash):
            bash = "bash"
        self.output.info(f"rocminfo consumer e2e driver: {bash} test.sh")
        self.run(f"{bash} test.sh", env="conanrun")
