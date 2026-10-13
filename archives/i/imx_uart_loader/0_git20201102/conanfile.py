#!/usr/bin/env python3
"""Conan recipe for imx_uart_loader 0_git20201102 on HarmonyOS PC.

imx_uart is the serial (UART) boot loader for the NXP i.MX5/6/7/8 families,
shipped inside the upstream `imx_usb_loader` project by Boundary Devices. The
upstream Makefile builds two binaries from one tree:

    imx_usb  : imx_usb.o imx_sdp.o imx_sdp_simulation.o imx_loader_config.o sdp.o sdps.o
    imx_uart : imx_uart.o imx_sdp.o imx_loader_config.o sdp.o

This recipe packages the UART variant only, matching the Alpine `imx_loader`
source package's `imx_uart_loader` subpackage, which owns exactly
/usr/bin/imx_uart (the USB variant lives in a separate `imx_usb_loader`
subpackage together with /etc/imx-loader.d).

OHOS-specific adaptations:
  - R26 does NOT apply: imx_uart is not a system-same-name library, it is a
    terminal tool with no library deliverable, so the Conan-managed dynamic
    link of its one dependency is correct rather than a forced static build.
  - The compiler comes from tools.build:compiler_executables (R33), never from
    a bare $CC in the environment.
  - CONFIG_SHELL is honoured for the test harness (R5): OHOS has no guaranteed
    /bin/sh for a non-trivial script.
  - make is driven with USBCFLAGS/USBLDFLAGS passed on the command line rather
    than through pkg-config: the upstream Makefile resolves libusb via
    `pkg-config --cflags/--libs libusb-1.0`, and pkg-config is not guaranteed
    to exist on the OHOS target or to see the Conan package. A command-line
    assignment overrides the Makefile's `=` definition.
  - The tool is linked with an explicit DT_RUNPATH pointing at the libusb
    package's lib/, because a bare CLI tool is not covered by the farm's
    LD_LIBRARY_PATH wrapper the way a library consumer is.
  - The upstream test suite under tests/ is executed from build(). It drives
    the *imx_usb* binary through the project's built-in SDP simulation
    (`imx_usb -v -S 0x15a2:0x0061 <image>`), so imx_usb is built here even
    though it is not packaged. See notes.md for exactly what that does and
    does not cover of the packaged imx_uart binary.
"""
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# Conan's can_run() compares the host settings with the *build profile*, and
# this farm deliberately uses the OHOS profile for both contexts (the device
# builds natively, so there is no separate build platform there). That makes
# can_run() report True even when we are cross-compiling from an x86_64 host,
# so it cannot be used to decide whether the freshly built aarch64 binaries can
# actually be executed. Compare the target arch against the real machine
# instead: on the Harmony PC it matches and the suite runs; on an x86_64 build
# host it does not and the suite is deferred to the device verify.
_TARGET_MACHINES = {
    "armv8": ("aarch64", "arm64"),
    "armv7": ("armv7l", "armv7", "armv6l"),
    "x86_64": ("x86_64", "amd64"),
}
from conan.tools.layout import basic_layout


class ImxUartLoaderConan(ConanFile):
    name = "imx_uart_loader"
    version = "0_git20201102"
    description = "Serial (UART) boot loader for NXP i.MX5/6/7/8 series SoCs."
    license = "LGPL-2.1-only"
    homepage = "https://github.com/boundarydevices/imx_usb_loader"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must be an explicit allow-list
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"imx_uart_loader supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # libusb is required to LINK imx_usb, the USB variant that the upstream
        # tests/ harness drives through the SDP simulation. The packaged
        # imx_uart binary itself does not reference libusb (neither imx_uart.c
        # nor sdp.c include <libusb.h>; only imx_usb.c does, and the upstream
        # link line for imx_uart omits $(USBLDFLAGS)).
        self.requires("libusb/1.0.27")

    def layout(self):
        basic_layout(self)
        # The upstream tree builds in-source with a plain Makefile.
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        # The GitHub codeload URL is extension-less, so give Conan an explicit
        # .tar.gz filename to select the right decompressor.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename=f"imx_usb_loader-{self.version}.tar.gz")

    def _cc(self):
        # R33: take the compiler from Conan conf, never a bare environment var
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        return compilers.get("c", "clang") if compilers else "clang"

    def _shell(self):
        # R5: OHOS has no guaranteed /bin/sh for complex scripts; prefer the
        # profile-provided CONFIG_SHELL, then bash, then the hnp bash path.
        return (os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash")

    def _target_runs_here(self):
        """True when the built binaries can actually execute on this machine."""
        expected = _TARGET_MACHINES.get(str(self.settings.arch))
        if not expected:
            return False
        return platform.machine().lower() in expected

    def build(self):
        apply_conandata_patches(self)

        cc = self._cc()
        libusb = self.dependencies["libusb"]
        usb_inc = os.path.join(libusb.package_folder, "include")
        usb_lib = os.path.join(libusb.package_folder, "lib")
        # libusb installs its headers under include/libusb-1.0/.
        usb_inc_full = os.path.join(usb_inc, "libusb-1.0")

        usbcflags = f"-I{usb_inc} -I{usb_inc_full}"
        usbldflags = f"-L{usb_lib} -lusb-1.0 -Wl,-rpath,{usb_lib}"

        # Build both binaries: imx_uart is the deliverable, imx_usb is what the
        # upstream test harness exercises.
        self.run(
            f"make CC='{cc}' "
            f"USBCFLAGS='{usbcflags}' USBLDFLAGS='{usbldflags}' "
            f"all",
            cwd=self.source_folder,
        )

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream tests/ harness (make -C tests tests).

        tests/Makefile:  tests: test.imx.test test-dcd.imx.test test-plugin.imx.test
        Each %.test runs `$(IMX_USB) -v -S 0x15a2:0x0061 <image>` and diffs the
        output against the checked-in golden <image>.output. IMX_USB defaults to
        ../imx_usb; pass it explicitly so the harness cannot silently pick up a
        stale or absent binary in another directory.
        """
        if not self._target_runs_here():
            # Cross-compiling from a non-OHOS host: the freshly built binaries
            # are aarch64 OHOS ELFs and cannot be executed here, so the harness
            # would fail with "Exec format error" (make Error 126) rather than
            # report anything about the code. The farm's device verify builds
            # and runs natively on the Harmony PC, where the machine matches the
            # target and this suite executes for real - it is not skipped there.
            self.output.info(
                "target arch %s cannot execute on %s; upstream tests/ suite "
                "will run in the native device verify"
                % (self.settings.arch, platform.machine())
            )
            return

        imx_usb = os.path.join(self.source_folder, "imx_usb")
        if not os.path.isfile(imx_usb):
            raise ConanException(
                f"upstream test harness needs {imx_usb}, which was not built"
            )

        libusb = self.dependencies["libusb"]
        libusb_lib = os.path.join(libusb.package_folder, "lib")

        shell = self._shell()
        # OHOS /tmp is a read-only erofs mount, so keep every scratch path
        # inside the build folder and honour an inherited TMPDIR.
        tmpdir = self.build_folder
        os.makedirs(tmpdir, exist_ok=True)

        # IMX_USB must stay RELATIVE, exactly as upstream's default
        # (`IMX_USB ?= ../imx_usb`). imx_usb derives the directory it loads its
        # .conf files from out of argv[0] (see get_base_path(argv[0]) in
        # imx_uart.c / imx_usb.c), and the harness echoes those config paths
        # into the output that is then diffed against the checked-in golden
        # files. The goldens record the relative rendering
        # ("config file <..//imx_usb.conf>"); passing an absolute path makes
        # the run print the absolute path instead and the diff fails on path
        # strings alone, with every protocol byte still matching.
        # The absolute path is used only to assert the binary exists.
        self.run(
            f"TMPDIR={tmpdir} LD_LIBRARY_PATH={libusb_lib}:$LD_LIBRARY_PATH "
            f"make -C tests tests IMX_USB='../imx_usb' SHELL='{shell}'",
            cwd=self.source_folder,
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)

        # The UART loader is the deliverable of this recipe (Alpine's
        # imx_uart_loader subpackage owns exactly this one path).
        shutil.copy2(os.path.join(self.source_folder, "imx_uart"),
                     os.path.join(bindir, "imx_uart"))

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
