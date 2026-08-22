import os
from conan import ConanFile


class BwmNgTestConan(ConanFile):
    """test_package for bwm-ng executable.

    bwm-ng is a CLI tool (not a library), so the consumer test invokes the
    installed binary's --version / --help and confirms the static ELF build
    is runnable on OHOS. Per R34, this must really exercise the installed
    package — `echo ok` would be caught by the L1e reverse-validation gate.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the installed bwm-ng binary in the package's bin/ dir.
        # VirtualRunEnv's env file may not always surface dependency bindirs,
        # so resolve the path explicitly and prepend it to PATH for the test.
        dep = self.dependencies[self.tested_reference_str]
        pkg_bin = os.path.join(dep.package_folder, "bin")
        sh = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Run test.sh with the bwm-ng bin dir prepended to PATH.
        # We do this via `env PATH=<bin>:$PATH bash test.sh` because conan
        # run() doesn't accept extra env vars per command.
        cmd = f"PATH='{pkg_bin}:'\"$PATH\" {sh} test.sh"
        self.run(cmd, env="conanrun")