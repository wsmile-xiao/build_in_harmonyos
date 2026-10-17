import os

from conan import ConanFile


class PconsoleTestConan(ConanFile):
    """test_package for pconsole 1.2.0.

    R34: the tests must substantially exercise the tested package.  Two layers:

    * test.sh            — the installed artifacts (ELF + pconsole.sh + ssh.sh +
                          licenses) and the script-level behaviour.
    * pconsole_pty_test.py — the pconsole binary itself.  pconsole refuses to
                          start unless it has an effective uid of 0 and a tty on
                          stdin, so every functional case is driven through a real
                          pseudo-terminal; the harness also inspects the ELF
                          directly (no readelf needed on the worker).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = os.path.join(self.dependencies["pconsole"].package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test.sh")
        harness = os.path.join(self.recipe_folder, "pconsole_pty_test.py")
        self.run('sh "%s" "%s"' % (script, bindir), env="conanrun")
        self.run('python3 "%s" "%s"' % (harness, bindir), env="conanrun")
