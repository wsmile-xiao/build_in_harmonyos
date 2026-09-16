# GCC Ada build-only GNAT seed under HarmonyOS XPM

## Scope

This draft records the GCC Ada 9.5.0 bootstrap path used by issue #2281. The
Ada frontend cannot be built by a C-only compiler, so the recipe uses a
checksum-pinned Alpine AArch64/musl GNAT 9.3 seed only during `conan create`.

## Failure signature

The seed and its five non-system dependencies were signed, but a Python
launcher still failed before `gnatmake` started:

```text
PermissionError: [Errno 13] Permission denied
MAP_XPM mmap: EACCES
PROT_READ | PROT_EXEC mmap: EACCES
```

Moving the same files from HMDFS to `/data/storage/el2/base/cache` and then to
the HAP `files` directory did not change the result. This ruled out a simple
directory-permission explanation.

## Root cause

The failed mmap calls ran in the Python launcher process. Their XPM owner
identity therefore differed from the signed GNAT seed and its signed
dependencies. The package-owned musl loader already contained the required
`check_xpm(fd)` path. Performing the same check in Python was both redundant
and early: clean CI never reached the seed loader.

## Working sequence

1. Verify every Alpine APK with its pinned SHA-256.
2. Copy only the required seed closure to executable application storage.
3. Shorten the five long ELF NEEDED names to names that fit in place.
4. Build the package-owned AArch64 musl loader with MAP_XPM support.
5. Rewrite each seed PT_INTERP to `/proc/self/fd/9`.
6. Sign the copied seed ELF files, short-name libraries, and loader.
7. In the launcher, open the loader on inheritable fd 9 and immediately exec
   the signed seed. Do not pre-map dependency code from Python.
8. Let the loader perform XPM checks while resolving dependencies under the
   signed seed process context.
9. Exclude the complete seed closure from the final Conan package.

## Evidence

- Device diagnostic r53 produced `seed_probe.o` and
  `SHORT_NEEDED_DIAGNOSTIC=pass`.
- Clean CI runs with Python-side XPM pre-mapping failed with EACCES in cache
  and HAP files locations.
- Commit `2da8d6c871` removed only the duplicate Python pre-map.
- Clean CI #31486 then completed the full GCC Ada source build and
  `test_package` successfully.

## Non-solutions

- Retrying the same Python mmap from a different writable directory.
- Priming fs-verity with a Python `PROT_EXEC` mapping.
- Shipping the Alpine seed in the final package.
- Removing code signing or bypassing the XPM gate.
