#!/usr/bin/env python3
"""Conan test_package for acpi_call 1.2.2.

acpi_call is a **Linux kernel module** (acpi_call.ko).  Its only consumer is
the kernel itself: userspace talks to it by writing ACPI method names to the
/proc/acpi/call interface, which the module exposes after it is *insmod*-ed
into a running kernel.  That loading + invocation can ONLY happen on a real
device with matching kernel headers + root — it is impossible inside the
OHOS cross-compile CI worker (no kernel tree, no insmod, no /proc/acpi/call).

Per the adaptation rules (R34/R9) a test_package MUST call the package's API
or execute its binary, and MUST NOT fake a pass.  Since acpi_call has no
userspace binary and no callable userspace API, we do the only honest thing:

  1. Run a REAL check (via self.run) that the packaged kernel-module source
     carries the /proc/acpi/call handler, ACPI evaluation entry point, and
     local parser/result-formatting safety invariants.  A missing source is
     a hard failure (exit 2), never a skipped pass.
  2. Explicitly report that kernel-state load/invoke verification remains
     0/1 and is not executed in CI.

The CI test_package result therefore means "source contract: 11/11 assertions
passed", not "kernel module functionality: passed".
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanException


class AcpiCallTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["acpi_call"].package_folder

        # Locate the packaged, safety-hardened source snapshot.
        module_c = os.path.join(pkg_folder, "src", "acpi_call.c")
        if not os.path.isfile(module_c):
            for root, _dirs, files in os.walk(pkg_folder):
                if "acpi_call.c" in files:
                    module_c = os.path.join(root, "acpi_call.c")
                    break

        if not os.path.isfile(module_c):
            raise ConanException(
                "[acpi_call] BLOCKED: packaged acpi_call.c is missing "
                f"(looked under {pkg_folder}); no source-contract assertion ran"
            )

        # Real execution (not an echo/print/true stub): grep the packaged
        # source for its module and safety contract.  Missing source (exit 2)
        # or a broken contract (exit 1) must fail the test_package gate.
        check_sh = os.path.join(self.source_folder, "check_source.sh")
        try:
            os.chmod(check_sh, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        except OSError:
            pass
        try:
            self.run(f'sh "{check_sh}" "{module_c}"', env="conanrun")
        except Exception as exc:
            raise ConanException(
                "[acpi_call] BLOCKED: source-contract check did not pass; "
                f"kernel functionality remains unverified: {exc}"
            ) from exc

        # Source assertions passed; kernel-state load/invoke remains unverified.
        self.output.warning(
            "[acpi_call] PARTIAL: source contract verified (11/11 assertions). "
            "Kernel load/invoke requires a real device with matching kernel "
            "headers + root; functional verification remains 0/1."
        )
