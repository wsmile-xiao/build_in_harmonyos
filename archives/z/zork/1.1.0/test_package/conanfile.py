from conan import ConanFile
from conan.tools.layout import basic_layout
import os
import shutil


class ZorkTestConan(ConanFile):
    name = "zork_test"
    version = "1.0"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder="src")

    def build(self):
        pass

    def test(self):
        # Consumer case: run zork smoke test using conanrun env
        dep = self.dependencies["zork"]
        zork_bin = os.path.join(dep.package_folder, "bin", "zork")
        self.output.info(f"Running zork smoke test: {zork_bin}")

        # Test 1: binary exists and is executable
        assert os.path.isfile(zork_bin), f"zork binary not found: {zork_bin}"
        assert os.access(zork_bin, os.X_OK), f"zork binary not executable: {zork_bin}"
        self.output.info("PASS: zork binary exists and is executable")

        # Test 2: run smoke test via self.run() with conanrun env
        out_path = os.path.join(self.build_folder, "zork_output.txt")
        cmd = f'printf "LOOK\\nQUIT\\nY\\n" | timeout 10 "{zork_bin}" > "{out_path}" 2>&1'
        self.run(cmd, env="conanrun")

        output = open(out_path, "r").read()
        self.output.info(f"Exit code: 0")

        # Test 3: verify expected output
        assert "Welcome to Dungeon" in output, f"Missing 'Welcome to Dungeon'"
        self.output.info("PASS: Welcome to Dungeon")
        assert "white house" in output, f"Missing 'white house'"
        self.output.info("PASS: white house")
        assert "mailbox" in output, f"Missing 'mailbox'"
        self.output.info("PASS: mailbox")
        assert "game is over" in output, f"Missing 'game is over'"
        self.output.info("PASS: game is over")
        self.output.info("zork smoke test passed — all assertions passed")

        # Cleanup: remove output file to avoid polluting git tree
        shutil.rmtree(self.build_folder, ignore_errors=True)
