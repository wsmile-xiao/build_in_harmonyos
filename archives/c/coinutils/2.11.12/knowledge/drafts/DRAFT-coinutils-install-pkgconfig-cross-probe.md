# DRAFT-coinutils-install-pkgconfig-cross-probe

> Contributor: coinutils 2.11.12 adaptation | Status: Draft | Updated: 2026-09-08
> Source: archives/c/coinutils/2.11.12

## Symptom

CoinUtils 2.11.12 installs legacy COIN-OR metadata from a generated
`install-data-hook`. The hook runs:

```make
PKG_CONFIG_PATH=...:$(DESTDIR)$(pkgconfiglibdir) "$(PKG_CONFIG)" --libs coinutils > coinutils_addlibs.txt
```

This happens while the package is being staged into `DESTDIR`.

## Root Cause

The hook treats pkg-config as an install-time introspection tool. During Conan
packaging, the staged tree is not a normal target runtime prefix, and pkg-config
may see incomplete metadata, host paths, system paths, or no target-capable
runtime at all. The resulting `coinutils_addlibs.txt` is legacy metadata, while
the Conan recipe already has a precise consumer contract in `package_info()`.

For HarmonyOS, the safer contract is:

- library: `CoinUtils`
- CMake target: `coinutils::coinutils`
- pkg-config name: `coinutils`
- include directories: `include` and `include/coin`
- system library for static package: `m`

## Recommended Handling

Patch generated `CoinUtils/Makefile.in` to neutralize the install-time
pkg-config command. Keep package metadata in Conan:

```python
self.cpp_info.set_property("cmake_target_name", "coinutils::coinutils")
self.cpp_info.set_property("pkg_config_name", "coinutils")
self.cpp_info.libs = ["CoinUtils"]
self.cpp_info.includedirs = ["include", os.path.join("include", "coin")]
```

If a downstream COIN-OR package really consumes `*_addlibs.txt`, generate that
file deterministically from the known Conan dependency graph instead of running
pkg-config during staging.

## Evidence

CoinUtils 2.11.12 applied `patches/0001-no-check-pkgconfig.patch`, built and
packaged `libCoinUtils.a`, and the CMakeDeps consumer resolved
`coinutils::coinutils`, `bzip2::bzip2`, and `ZLIB::ZLIB` successfully in shadow
CI.

The target smoke test printed:

```text
CoinPackedMatrix::getNumElements() = 0
OK: coinutils 2.11.12 smoke test passed.
```

## Reuse Boundary

This is a packaging-time fix for generated COIN-OR install hooks. It is not a
general reason to remove pkg-config files from every package. If pkg-config
metadata is part of the public contract, preserve it through Conan metadata or a
deterministic generated file.
