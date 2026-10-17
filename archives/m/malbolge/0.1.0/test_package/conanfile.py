import os

from conan import ConanFile


class MalbolgeTestConan(ConanFile):
    """test_package for the malbolge interpreter — runs test.sh which
    executes the real OHOS-built malbolge binary against the official
    nop.mal fixture, a derived ASCII whitespace-nop fixture, and error
    paths (no-args / missing-file / invalid-source)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution. Resolve CONFIG_SHELL from env
        # (set by the OHOS profile's [buildenv]), fall back to PATH lookup.
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh", env="conanrun")
