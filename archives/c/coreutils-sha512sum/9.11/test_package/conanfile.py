import os

from conan import ConanFile


class CoreutilsSha512sumTestConan(ConanFile):
    """test_package for coreutils-sha512sum — runs test.sh/test_ohos.sh against
    the package's own binary (absolute path from package_folder), not a PATH lookup."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _package_binary(self):
        """Absolute path to the package's own sha512sum binary (R34/L1e: the
        test must depend on the package artifact, not a system PATH lookup)."""
        dep = self.dependencies[self.tested_reference_str]
        return os.path.join(dep.package_folder, "bin", "sha512sum")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        binary = self._package_binary()
        if not os.path.exists(binary):
            raise Exception("package binary missing: " + binary)
        self.run(f"{bash} test.sh {binary}", env="conanrun")
        self.run(f"{bash} test_ohos.sh {binary}", env="conanrun")
