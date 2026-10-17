import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import load, save


class ClazyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["clazy"].package_folder
        standalone = os.path.join(pkg, "bin", "clazy-standalone")
        plugin = os.path.join(pkg, "lib", "ClazyPlugin.so")

        # Verify artifacts exist
        assert os.path.exists(standalone), f"clazy-standalone not found at {standalone}"
        assert os.path.exists(plugin), f"ClazyPlugin.so not found at {plugin}"

        if not can_run(self):
            return

        # Run the external test script for ELF verification + version check
        shell = os.environ.get("CONFIG_SHELL", "sh")
        script_src = os.path.join(self.source_folder, "test_clazy.sh")
        script = os.path.join(self.build_folder, "test_clazy.sh")
        script_text = load(self, script_src).replace("\r\n", "\n").replace("\r", "\n")
        save(self, script, script_text)
        self.run(f'"{shell}" "{script}" "{standalone}" "{plugin}"', env="conanrun")
