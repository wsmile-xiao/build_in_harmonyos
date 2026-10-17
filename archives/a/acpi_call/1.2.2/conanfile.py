#!/usr/bin/env python3
"""Conan recipe for acpi_call 1.2.2 — Linux ACPI kernel module.

acpi_call is a Linux kernel module (Kbuild) that exposes ACPI method calls
via /proc/acpi/call.  It requires Linux kernel headers to compile and loads
as acpi_call.ko.

NOTE: HarmonyOS (OHOS) does not ship Linux kernel headers suitable for
external Kbuild module compilation.  The build is therefore a no-op, but the
recipe exports and packages a source snapshot based on the pinned upstream
commit with parser and result-formatting safety hardening.  The test_package
can verify that source contract without claiming that the module was built or
loaded.

Upstream: https://github.com/nix-community/acpi_call (VERSION=1.2.2)
Original: https://github.com/mkottman/acpi_call (inactive since 2013)
License:  GPL-3.0-or-later
"""

import os

from conan import ConanFile
from conan.tools.files import copy


class AcpiCallConan(ConanFile):
    name = "acpi_call"
    version = "1.2.2"
    description = (
        "Linux kernel module to call ACPI methods via /proc/acpi/call. "
        "Requires Linux kernel headers — builds as no-op on HarmonyOS."
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/nix-community/acpi_call"
    url = ""  # CI fills this

    package_type = "shared-library"  # kernel module (.ko)

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "acpi_call.c"

    def source(self):
        # acpi_call.c is based on the tarball pinned in conandata.yml and
        # includes local parser and result-formatting hardening.  Conan has
        # already copied it to the source folder, so no network download is
        # needed.
        pass

    def build(self):
        # acpi_call is a Kbuild kernel module (obj-m := acpi_call.o).
        # It requires Linux kernel headers (linux/module.h, linux/acpi.h)
        # which are not available in the OHOS sysroot.
        # Build is intentionally empty — there is nothing to compile
        # without kernel headers.
        pass

    def package(self):
        # The kernel module cannot be built without kernel headers.  Export the
        # safety-hardened source snapshot (declared by exports_sources above)
        # so consumers and the test package can inspect the module contract
        # rather than treating an empty package as a passed check.
        copy(self, "acpi_call.c", src=self.source_folder,
             dst=os.path.join(self.package_folder, "src"))

    def package_info(self):
        # Kernel module — no user-visible C/C++ library.
        pass
