# acpi-override

Conan application package for the Debian `acpi-override-initramfs` hook.
This is a POSIX shell/initramfs integration package, not a C++ library.

The device must provide `initramfs-tools-core`, `cpio`, and an early-initramfs
ACPI override mechanism for full runtime validation.
