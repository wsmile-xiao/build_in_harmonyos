# libtypec

C library providing a userspace interface to the Linux USB Type-C and USB
Power Delivery subsystem. It exposes connector capabilities, source/sink PDOs,
connector status and alternate-mode information through `/sys/class/typec` and
debugfs.

- **Upstream:** https://github.com/Rajaram-Regupathy/libtypec
- **License:** MIT
- **Build system:** Meson (library only; CMake also ships upstream)
- **Hard dependency:** libudev (provided by `eudev/3.2.14`)

## OHOS adaptation status

Only the shared library is cross-compiled. The diagnostic tools in `utils/`
(`lstypec`, `typecstatus`, `ucsicontrol`, `usbcview`) are not built: they walk
the kernel Type-C sysfs class that does not exist on OHOS, and `usbcview`
additionally requires GTK3.

Runtime behaviour requires a real Type-C controller; on OHOS the package is
validated for compilation, linking and loader acceptance only.
