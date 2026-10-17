import os

from conan import ConanFile


class LsmountTestConan(ConanFile):
    """test_package for the lsmount executable package.

    test.sh runs the **installed** lsmount binary (PATH comes from the package's
    cpp_info.bindirs via the conanrun environment) and asserts on its exit codes
    and on the exact content it renders — see test_package/test.sh (T1..T9).
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries here, and the
        # upstream shebang target is not guaranteed. Run the suite through the
        # shell Conan tells us to use, falling back to the OHOS bash location.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
