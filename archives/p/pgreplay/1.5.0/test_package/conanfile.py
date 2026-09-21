import os
import shutil

from conan import ConanFile


class PgreplayTestConan(ConanFile):
    """Consumer test for the pgreplay executable.

    Drives the packaged binary through its two offline public entry points:
    log parsing (-f, writes a binary replay file) and dry-run replay
    (-r -n, exercises the replay consumer without a database connection).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = shutil.which("bash") or "bash"
        scratch = os.path.join(self.build_folder, "scratch")
        os.makedirs(scratch, exist_ok=True)
        script = os.path.join(self.source_folder, "test_pgreplay.sh")
        # seed PWD: bash start-getcwd() fails under HMDFS (经验汇总 §12.73③)
        self.run(
            f'cd "{scratch}" && PWD="{scratch}" "{bash}" "{script}"',
            env="conanrun",
        )
