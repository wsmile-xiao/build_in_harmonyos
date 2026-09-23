import os

from conan import ConanFile


class BruteforceWalletTestConan(ConanFile):
    """test_package for bruteforce-wallet — runs the built binary (R34).

    Invokes test.sh which executes `bruteforce-wallet` three times (-h
    usage/version banner, missing-arg error, unknown-option error) and
    asserts on the real program output.
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Preflight box has no `bash` on PATH (only /bin/sh guaranteed);
        # test.sh is POSIX sh compatible, so run it with sh.
        # Resolve order CONFIG_SHELL -> SHELL -> /bin/sh, ignoring
        # non-existent profile paths such as /data/service/hnp/bin/bash.
        shell = "/bin/sh"
        for var in ("CONFIG_SHELL", "SHELL"):
            cand = os.environ.get(var)
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                shell = cand
                break
        self.run(f"{shell} test.sh", env="conanrun")
