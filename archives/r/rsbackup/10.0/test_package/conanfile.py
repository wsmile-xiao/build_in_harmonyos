import tempfile
from pathlib import Path

from conan import ConanFile
from conan.tools.env import Environment, VirtualRunEnv


class RsbackupTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        rsbackup = Path(self.dependencies["rsbackup"].package_folder) / "bin/rsbackup"
        rsync = Path(self.dependencies["rsync"].package_folder) / "bin/rsync"
        if not rsbackup.is_file() or not rsync.is_file():
            raise RuntimeError("Required backup executables are absent")
        env = Environment()
        env.define("RSBACKUP_BIN", str(rsbackup))
        env.define("RSYNC_BIN", str(rsync))
        with tempfile.TemporaryDirectory(prefix="rsbackup-e2e-") as test_dir:
            env.define("RSBACKUP_TEST_DIR", test_dir)
            with VirtualRunEnv(self).vars().apply(), env.vars(self).apply():
                self.run("bash test_e2e.sh", cwd=self.source_folder)
