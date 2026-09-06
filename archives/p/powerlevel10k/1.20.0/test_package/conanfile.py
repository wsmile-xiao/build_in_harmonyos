import os

from conan import ConanFile


class Powerlevel10kTestConan(ConanFile):
    """test_package for powerlevel10k — R34 smoke suite (consumer perspective).

    Exercising the installed share/powerlevel10k tree for real: upstream
    layout integrity, zsh syntax checks on the core scripts, and an actual
    theme load inside a clean zsh (GITSTATUS_AUTO_INSTALL=0 — never
    download/build gitstatusd at test time) asserting the p10k entry
    function and a ready vcs backend (native vcs_info fallback when the
    gitstatusd daemon is absent, which is the packaged configuration;
    see ../notes.md).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["powerlevel10k"].package_folder
        theme_dir = os.path.join(pkg, "share", "powerlevel10k")
        # Wrap with bash like posh/aurpublish test_package precedent
        # (OHOS has no /bin/bash interpreter path guarantees).
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run('"{}" test.sh {}'.format(bash, theme_dir), env="conanrun")
