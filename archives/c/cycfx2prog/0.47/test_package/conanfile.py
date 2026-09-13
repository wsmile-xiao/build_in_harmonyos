import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class Cycfx2progTestConan(ConanFile):
    """test_package for the cycfx2prog executable.

    cycfx2prog has NO upstream test suite (the 2009 tarball is four files and
    the Makefile only defines all/clean/distclean/dist). The real programming
    path needs a physical Cypress EZ-USB FX2 chip on the USB bus, which no CI
    sandbox can provide. What IS verifiable without hardware is the CLI
    contract plus the libusb runtime path: `--help`/`--version` return 0
    without touching libusb at all, while `--list` really calls
    usb_init()/usb_find_busses()/usb_find_devices() through libusb-compat ->
    libusb-1.0, and the no-device paths must fail cleanly with exit code 1.
    test.sh exercises exactly those paths.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably;
        # use bash (CONFIG_SHELL comes from the profile's [buildenv]).
        # cwd is explicit: with basic_layout() the test runs from
        # <test_package>/build-release, not from the test_package source dir.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" test.sh', cwd=self.source_folder, env="conanrun")
