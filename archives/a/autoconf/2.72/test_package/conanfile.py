import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class AutoconfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    exports_sources = "test.sh"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def generate(self):
        env = Environment()
        autoconf_bin = os.path.join(self.dependencies.build["autoconf"].package_folder, "bin")
        env.prepend_path("PATH", autoconf_bin)
        env.define_path("AUTOCONF_BIN_DIR", autoconf_bin)

        m4_bin = os.path.join(self.dependencies.build["m4"].package_folder, "bin")
        env.prepend_path("PATH", m4_bin)
        env.define_path("M4", os.path.join(m4_bin, "m4"))

        perl_bin = os.path.join(self.dependencies.build["perl"].package_folder, "bin")
        env.prepend_path("PATH", perl_bin)
        env.define_path("PERL", os.path.join(perl_bin, "perl"))

        shell = self._config_shell()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        env.vars(self).save_script("autoconf_test_env")

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: autoconf runtime smoke skipped")
            return

        self.run("sh test.sh", env=["conanbuild", "autoconf_test_env"])

    @staticmethod
    def _config_shell():
        for shell in ("/bin/sh", "/system/bin/sh", "sh"):
            if not os.path.isabs(shell) or os.access(shell, os.X_OK):
                return shell
        return "sh"
