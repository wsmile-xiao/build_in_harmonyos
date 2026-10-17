import os

from conan import ConanFile


class Lpc21ispTestConan(ConanFile):
    """test_package for lpc21isp executable — runs test.sh which invokes the binary.

    lpc21isp is a serial-port flash tool for NXP LPC microcontrollers. It has
    no upstream test suite, and the real flash path needs physical hardware +
    a serial port. The verifiable, hardware-independent CLI contract is:
    with fewer than 5 argv entries, ReadArguments() prints the version banner
    + full usage and exits 1 WITHOUT opening any serial port. test.sh checks
    CLI startup, the version banner, usage syntax, argument parsing and
    graceful handling of an unknown option.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        # Use bash to wrap binary execution (CONFIG_SHELL from profile = bash).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
