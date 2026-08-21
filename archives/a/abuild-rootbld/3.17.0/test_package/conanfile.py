import os

from conan import ConanFile
from conan.errors import ConanException


class AbuildRootbldTestConan(ConanFile):
    """test_package for abuild-rootbld — verifies the dependency contract.

    rootbld is a noarch meta-package: the actual `abuild rootbld` command is
    provided by the abuild dependency. The smoke test asserts:
      1. the installed bin/rootbld wrapper exists and --version runs,
      2. runtime deps are present: bwrap (bubblewrap), envsubst (gettext),
         abuild (abuild package).
    """
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["abuild-rootbld"]
        bindir = os.path.join(dep.package_folder, "bin")

        # 1. rootbld wrapper must exist and report version
        rootbld = os.path.join(bindir, "rootbld")
        if not os.path.isfile(rootbld):
            raise ConanException(f"rootbld wrapper not found in {bindir}")
        rc = self.run(f'"{rootbld}" --version 2>&1', env="conanrun",
                      ignore_errors=True)
        if rc != 0:
            raise ConanException("rootbld --version failed to execute")
        self.output.info("rootbld --version: OK")

        # 2. bwrap (bubblewrap dep) must be present
        bwrap = os.path.join(
            self.dependencies["bubblewrap"].package_folder, "bin", "bwrap")
        if not os.path.isfile(bwrap):
            raise ConanException("bwrap not found (bubblewrap dependency)")
        rc = self.run(f'"{bwrap}" --version > /dev/null 2>&1', env="conanrun",
                      ignore_errors=True)
        if rc != 0:
            raise ConanException("bwrap --version failed")
        self.output.info("bwrap: OK")

        # 3. envsubst (gettext dep) must be present
        envsubst = os.path.join(
            self.dependencies["gettext"].package_folder, "bin", "envsubst")
        if not os.path.isfile(envsubst):
            raise ConanException("envsubst not found (gettext dependency)")
        rc = self.run(f'"{envsubst}" --version > /dev/null 2>&1', env="conanrun",
                      ignore_errors=True)
        if rc != 0:
            raise ConanException("envsubst --version failed")
        self.output.info("envsubst: OK")

        # 4. abuild (abuild dep) must be present
        abuild = os.path.join(
            self.dependencies["abuild"].package_folder, "bin", "abuild")
        if not os.path.isfile(abuild):
            raise ConanException("abuild not found (abuild dependency)")
        self.output.info("abuild: OK")

        # 5. Run committed test.sh wrapper
        test_sh = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sh")
        if os.path.isfile(test_sh):
            rc = self.run(f'sh "{test_sh}"', env="conanrun", ignore_errors=True)
            if rc != 0:
                raise ConanException(f"test.sh failed (exit {rc})")
            self.output.info("test.sh: OK")
