# wmgtemp — Window Maker Temperature Dockapp

wmgtemp is a 64x64 dockapp that graphically displays CPU and SYS
temperatures from lm_sensors. Originally written for the VIA686A chipset,
version 1.2 auto-detects sensors and works with any lm_sensors-supported
hardware.

## Build system

Autotools (autoconf 2.69 + automake). The `configure.ac` probes:
- `AC_PROG_CC`
- `AC_CHECK_LIB([sensors], [sensors_get_features])`
- `PKG_CHECK_MODULES([X11], [x11])`
- `PKG_CHECK_MODULES([dockapp], [dockapp])`

## OHOS adaptation

- wmgtemp 1.2 does not ship separate `config.guess`/`config.sub` files;
  platform detection is embedded directly in `configure`. The host triplet
  is passed via `--host=aarch64-linux-ohos`.
- `configure` is patched to use `umask 022` instead of `umask 077` (FUSE
  filesystems ignore chmod; `umask 077` makes `mktemp -d` create directories
  that cannot be written by child processes).
- `_restore_exec_bits()` re-chmods autotools helper scripts that lost their
  exec bit on HDFS extraction.
- `_prepare_linker_view()` stages `.so` and `.a` files in a conan-owned
  directory so `ld.lld` can open them regardless of HDFS task-mapping quirks.
- `PKG_CONFIG_PATH` is populated with conan-generated `.pc` files so
  `PKG_CHECK_MODULES` resolves without a system pkg-config database.
- lm-sensors ships only static libs (`libsensors.a`); its include/lib paths
  are passed via environment variables during configure and make.

## Dependencies

- `libdockapp/0.7.3` — dockapp framework (wmgeneral.h, misc.h, libdockapp.so)
- `lm-sensors/3.6.0` — libsensors.a and sensors/sensors.h (static only)
- `libx11/6.4.0`, `libxext/6.4.0`, `libxpm/3.5.17` — transitive via libdockapp

## License

Artistic License (per upstream `Artistic` file).
