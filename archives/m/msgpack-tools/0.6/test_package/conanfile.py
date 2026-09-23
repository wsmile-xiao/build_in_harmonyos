import os

from conan import ConanFile


class MsgpackToolsTestPackage(ConanFile):
    """test_package for msgpack-tools — runs test.sh (functional + OHOS-specific)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash (from CONFIG_SHELL profile env or PATH) to run the tests.
        bash = os.environ.get("CONFIG_SHELL", "bash")
        for script in ("test.sh", "ohos_test.sh"):
            self.run(f'{bash} "{os.path.join(self.source_folder, script)}"',
                     env="conanrun")
