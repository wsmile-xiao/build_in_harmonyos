#!/usr/bin/env python3
"""Consumer tests for the packaged leave 1.12 executable.

runs two independent entries against the *installed* package:

  * test_leave.sh          — generic consumer tests: 5 deterministic
                             invocations of bin/leave (invalid-argument
                             usage/exit-code checks, the no-argument+EOF
                             prompt path, and the valid "+6" scheduling path
                             whose forked nagging child is killed);
  * ohos_specific_test.py  — HarmonyOS-specific tests (R53), fail closed:
                             ELF64-LE-AArch64 identity, the musl program
                             interpreter, no RPATH/RUNPATH, and real execution
                             of the packaged binary on the OHOS PC asserting
                             the invalid-argument exit code, the no-argument
                             prompt path and the "+6" alarm announcement.

Both entries genuinely depend on the leave package: the CI L1e destructive
check (mv bin/ away, re-run) fails because the executable cannot be found.
"""

import os
import shutil

from conan import ConanFile


class LeaveTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = ("test_leave.sh", "ohos_specific_test.py")
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        executable = os.path.join(
            self.dependencies["leave"].package_folder, "bin", "leave"
        )
        workdir = self.source_folder

        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries reliably;
        # wrap the binary execution with bash (aa3d/lci pattern).  CONFIG_SHELL
        # comes from the profile buildenv, with a PATH lookup as fallback.
        bash = os.environ.get("CONFIG_SHELL", "") or shutil.which("bash") or "bash"
        self.run(
            '"{}" "{}" "{}" "{}"'.format(
                bash,
                os.path.join(workdir, "test_leave.sh"),
                executable,
                workdir,
            ),
            env="conanrun",
        )

        python = os.environ.get("CONAN_TEST_PYTHON3", "") or "python3"
        self.run(
            '"{}" "{}" "{}"'.format(
                python,
                os.path.join(workdir, "ohos_specific_test.py"),
                executable,
            ),
            env="conanrun",
        )
