import os

from conan import ConanFile


class OhcountTestConan(ConanFile):
    """Consumer test: runs the installed bin/ohcount (R34/R53).

    The package is an application, so there is nothing to link against; the
    test executes the packaged binary and asserts real counting results plus
    the HarmonyOS packaging properties (pure-python ELF checks).
    """
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = ("ohos_specific_test.py",)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(pkg.package_folder, "bin")
        python = os.environ.get("CONAN_TEST_PYTHON3", "") or "python3"
        self.run(
            f'"{python}" "{self.source_folder}/ohos_specific_test.py" "{bindir}"',
            env="conanrun",
        )
