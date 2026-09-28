import os

from conan import ConanFile


class PmountTestConan(ConanFile):
    """test_package for the pmount/pumount executables.

    pmount is a setuid-root wrapper by design, and both programs refuse any
    argument unless geteuid() is 0, so on OHOS -- where the packaged binaries
    cannot carry a setuid bit -- the only unprivileged code path is the
    no-argument enumeration of already-mounted removable devices.  These tests
    therefore assert one positive behaviour (that enumeration runs and parses
    /proc/mounts) and the privilege boundary itself (both tools must refuse an
    argument with the suid message).  See test.sh.
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so bash from
        # the hnp bin dir wraps the run (repo test_package-executable template).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("%s test.sh" % bash, env="conanrun")
