# E328 - Isolate MPICH Wrapper Flags From Worker-Local CPPFLAGS

## Symptom

An MPICH Conan build completes compilation and the full upstream test command,
then fails while packaging:

```text
Invalid configuration: mpicc contains non-relocatable paths:
/storage/Users/currentUser/usr/local
```

The wrapper was configured with
`CPPFLAGS=-I/storage/Users/currentUser/usr/local/include -DNDEBUG`, even though
that include directory belongs to the Buildbot Worker rather than the package.

## Root Cause

MPICH uses `PAC_PREFIX_ALL_FLAGS(WRAPPER)` during configure. That macro copies
the active `CPPFLAGS` into `WRAPPER_CPPFLAGS`, which is substituted into
`mpicc`, `mpicxx`, and the Fortran wrappers. Conan's OHOS profile supplies a
user-local include path for building generic packages. Allowing that profile
value to reach MPICH configure therefore turns a transient build input into
installed wrapper metadata.

The package-time forbidden-path check correctly rejected the leak. Removing or
downgrading that check would publish a wrapper coupled to one Worker's home
directory.

## Solution

Define the wrapper-persistent flags in the recipe-owned configure environment.
For MPICH 5.0.1.2, set `CPPFLAGS=-DNDEBUG`: it preserves the Release semantic
without importing an external include directory. The command-local assignment
overrides the profile value before configure snapshots `WRAPPER_CPPFLAGS`.

Retain the existing package-time scan for source, build, package, Conan-cache,
and Worker-local paths. If a future package genuinely requires an include flag,
parse and allowlist paths bound to the package or SDK rather than deleting a
hard-coded substring from the generated script.

## Validation

The directed fixture imports the production recipe, injects the Worker-local
path into the surrounding environment, and confirms that the configure command
still contains the controlled `CPPFLAGS=-DNDEBUG`. It then exercises the
production wrapper rewrite: a clean wrapper is rewritten to one relocatable
`-lpmi`, while reinserting the Worker path is rejected with the original
fail-closed error.

Final acceptance still requires the staged Pre-PR contract, independent W4,
current-HEAD AI Review, and exact-current-HEAD Buildbot success.

## Applicability

Use this pattern for Autoconf projects that persist build flags into compiler
wrappers or metadata. Do not erase flags blindly, weaken relocation checks, or
assume that a path valid on the Worker exists for package consumers.
