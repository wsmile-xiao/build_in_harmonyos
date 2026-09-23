import os

from conan import ConanFile


class PtyprocessTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_dir = os.path.dirname(os.path.abspath(__file__))
        smoke = os.path.join(test_dir, "smoke.py")
        ohos_test = os.path.join(test_dir, "test_ohos.py")
        self.run(f"python3 {smoke}", cwd=test_dir)
        self.run("python3 -m unittest test_ohos -v", cwd=test_dir)
