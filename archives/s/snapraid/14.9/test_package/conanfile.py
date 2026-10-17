import os
import subprocess

from conan import ConanFile


class SnapraidTestConan(ConanFile):
    """test_package for the snapraid executable — runs test.sh which
    drives the installed binary through a real sync/check/dup cycle."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # E386: probe for a shell that can getcwd() in the actual test
        # folder; the profile's CONFIG_SHELL (hnp bash) fails there on
        # HMDFS ("PWD: unbound variable" after a broken shell init).
        run_folder = self.build_folder
        shell = None
        for cand in (
            "/bin/sh",
            "/usr/bin/sh",
            "/usr/bin/bash",
            "/bin/bash",
            "/data/service/hnp/bin/bash",
        ):
            if not os.path.exists(cand):
                continue
            try:
                r = subprocess.run(
                    [cand, "-c", "pwd >/dev/null"],
                    cwd=run_folder,
                    capture_output=True,
                    timeout=20,
                )
            except Exception:
                continue
            if r.returncode == 0 and not r.stderr.strip():
                shell = cand
                break
        if shell is None:
            raise Exception("E386: no capability-tested shell for the test folder")
        script = os.path.join(run_folder, "test.sh")
        self.run("cd '%s' && '%s' '%s'" % (run_folder, shell, script), env="conanrun")
