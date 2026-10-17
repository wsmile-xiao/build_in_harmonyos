# acpi-override 0.1+nmu2

## Scope

`acpi-override` is a Debian-native POSIX shell hook, not a C++ library. The
package installs `acpi-override` under `share/initramfs-tools/hooks/` and an
empty `/var/lib/acpi-override/` directory for ACPI override tables.

## Dependencies

Runtime requires `initramfs-tools-core` (for `hook-functions` and
`prepend_earlyinitramfs`), `mktemp`, `find`, `cp`, `ls`, `cpio`, and a kernel
that supports early-initramfs ACPI table overrides. The Debian source declares
`debhelper-compat (= 13)` only for its native Debian build.

The portability patch replaces both upstream `mktemp ...XXXXXX` calls with
collision-resistant `mkdir`/PID paths because HarmonyOS Toybox `mktemp` does
not accept GNU template arguments.

## Device validation

The package recipe and SHA256 source verification are complete. Full execution
must be performed on the OHOS aarch64 device because the Windows host does not
provide Debian initramfs tools or `cpio`. Run the test package first; then place
validated ACPI tables in `/var/lib/acpi-override/` and run the hook through the
device's initramfs generation workflow. Record whether OHOS exposes an
equivalent early-initramfs injection path.

## Upstream tests

The upstream Debian-native source contains only the hook script and Debian
packaging metadata; it ships no automated test target or test cases. The
package test therefore executes the packaged hook with deterministic
`initramfs-tools` and `cpio` test doubles, asserting that an ACPI table is
staged below `kernel/firmware/acpi/` and produces a non-empty early-initramfs
payload.

## Path assessment

This is a normal Path A application adaptation. The Conan package and its
`test_package` verify source retrieval, hook installation, and the hook's
functional path on the OHOS device. Full initramfs generation remains an optional device-runtime
integration check: it requires the device to provide a compatible
`initramfs-tools-core` implementation and ACPI table override support. Missing
device capabilities must be reported as a runtime limitation, not treated as
an adaptation failure or a reason to claim Path B.
