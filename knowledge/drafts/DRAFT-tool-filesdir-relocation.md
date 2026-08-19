# Packaged Tool FILESDIR Relocation

## Evidence

`cppcheck/2.21.0` is installed with `share/Cppcheck/cfg/std.cfg`, but its executable retains a
build-time absolute `FILESDIR`.  When pixz runs the upstream `cppcheck-src.sh` test after the
original build cache is gone, cppcheck cannot locate `std.cfg`.

For pixz/1.0.7 on HarmonyOS PC, the recipe reads the trusted build-requirement executable,
validates the `FILESDIR` marker and the installed data layout, and restores that exact stale path
to the installed `share/Cppcheck` directory.  Symlink creation is used when supported; copying
the data directory is the fallback for a filesystem that rejects symlinks.

The original pixz source also dereferenced two `malloc()` results in `src/common.c` without a
NULL check.  The portability patch now terminates through the existing `die()` routine before
either pointer is dereferenced, so the upstream static analysis runs without suppressing those
warning IDs.

## Validation target

Run the upstream `make check` suite and require all four tests to pass:

1. `compress-file-permissions.sh`
2. `cppcheck-src.sh`
3. `single-file-round-trip.sh`
4. `xz-compatibility-c-option.sh`

Then run the packaged pixz compression/decompression round-trip test.

## Reuse criteria

Use this pattern only after confirming all of the following:

- the executable exposes a parseable, absolute FILESDIR marker;
- the package contains the required runtime data in a verified relative location;
- the stale target is absent, or already resolves to that exact data directory;
- the tool's upstream test is executed after relocation.
