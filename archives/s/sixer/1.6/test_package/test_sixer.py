import os
import subprocess
import sys
import unittest


if len(sys.argv) != 2:
    raise SystemExit(f"用法：{sys.argv[0]} <包目录>")
PACKAGE_FOLDER = sys.argv.pop(1)


class SixerPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = os.path.abspath(PACKAGE_FOLDER)
        cls.launcher = os.path.join(cls.package, "bin", "sixer")

    def test_installed_module_imports(self):
        import sixer

        self.assertEqual(sixer.MAX_RANGE, 1024)
        self.assertEqual(
            os.path.abspath(sixer.__file__),
            os.path.join(self.package, "lib", "python", "site-packages", "sixer.py"),
        )

    def test_generated_launcher_is_packaged(self):
        self.assertTrue(os.path.isfile(self.launcher))
        self.assertTrue(os.access(self.launcher, os.X_OK))

    def test_launcher_propagates_failure_status(self):
        missing_file = os.path.join(self.package, "missing.py")
        result = subprocess.run(
            [self.launcher, "--write", "xrange", missing_file],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_registered_command_runs(self):
        result = subprocess.run(
            [self.launcher, "--help"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage: sixer ", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
