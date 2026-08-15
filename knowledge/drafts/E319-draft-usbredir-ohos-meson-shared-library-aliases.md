# E319 - HarmonyOS Meson versioned shared-library aliases

> Status: DRAFT | Source: USBredir 0.15.0 PR #3016 | Evidence commit: `9ac97c8fbec8307483cd80c9c9b15085674d8a85`

## Error pattern

Meson typically creates one versioned shared-library file and two symbolic
links:

```text
libfoo.so.X.Y.Z
libfoo.so.X -> libfoo.so.X.Y.Z
libfoo.so   -> libfoo.so.X.Y.Z
```

On HarmonyOS target storage, creating or resolving the customary links can
fail. The real versioned ELF exists, but an upstream test, a consumer linker,
or the dynamic loader may request `libfoo.so.X` or `libfoo.so` and fail.

## Reusable remedy

For a Conan Meson recipe, apply this only when `settings.os == "OHOS"`:

1. Run `meson.build()`.
2. Scan the actual Meson output directories for real `libfoo.so.X.Y.Z` files.
   Do not descend into `*.so.*.p` object directories.
3. If absent, copy each real file to `libfoo.so.X` and `libfoo.so`.
4. Run native `meson.test()` only after those build-tree aliases exist.
5. Run `meson.install()`, then repeat the same absent-only copy in the package
   `lib/` directory before a consumer uses the package.

The implementation must not replace pre-existing files or alter the Conan
component/library declarations. The copies are an OHOS filesystem
compatibility layer, not a change to upstream ABI naming.

## Verified evidence

USBredir 0.15.0 implemented this as
`_copy_shared_library_aliases()` in its Conan recipe. The isolated HarmonyOS
PC transaction verified the official source SHA-256:

```text
6dc2a380277688a068191245dac2ab7063a552999d8ac3ad8e841c10ff050961
```

Both native `conan create` commands exited zero. Actual upstream Meson tests
were `2/2` (`filter`, `serializer`) and the installed parser consumer was
`1/1`. The retained raw reports are under:

```text
reports/pr-3016-9ac97c8fb-device-r5/
```

This evidence belongs only to commit `9ac97c8f`. PR #3016 was subsequently
rebased to `20facc03c0341f67baa9c7c6cb9620d9819f7765`; an exact-head device
rerun is required before publishing those rates for the current PR head.

## Boundary

This workaround solves library-name resolution only. In the same USBredir
consumer, the optional libusb host context reported `LIBUSB_ERROR_OTHER`
because the device has no usable usbfs backend. That result is a hardware or
platform capability limitation, not an alias-copy failure and must remain
separately reported.

## Related entries

- E316: copying a SONAME entity into a relocatable package.
- P016: HMDFS symbolic-link limitations require a compatible replacement.
