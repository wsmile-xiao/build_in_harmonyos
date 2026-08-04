# Boost 1.91.0 Redex dependency adaptation

## Scope

This recipe packages the Boost 1.91.0 components required by Redex
v2026.04.30: Regex, Filesystem, ProgramOptions, Iostreams, and Thread. It uses
the official revised CMake release asset `boost-1.91.0-1-cmake.tar.xz` with
its verified SHA-256 digest.

Redex uses Boost.Iostreams mapped files and generic filtering streams. It does
not use the gzip, bzip2, lzma, or zstd filters, so all four optional upstream
backends are disabled and the recipe has no external compression dependency.
Boost.Regex remains an upstream CMake interface target; the Conan component
therefore must not declare a nonexistent `libboost_regex` artifact.

## HarmonyOS contract

- `BOOST_THREAD_DONT_PROVIDE_INTERRUPTIONS=1` avoids unavailable POSIX thread
  cancellation APIs.
- Filesystem statx and copy-file-range probes are disabled in favor of the
  portable fallback paths.
- Explicit SONAME and build-tree RPATH flags repair CMake's generic HarmonyOS
  linker rules.
- The source patch prevents versioned shared-library symlinks on HarmonyOS,
  where the package filesystem cannot create the upstream link layout.
- Shared objects and runnable consumers are signed atomically when the native
  signing tools are available.

## Validation

The build runs the official ProgramOptions unit suite plus the upstream
Iostreams and Regex CMake integration flows. All 16 selected, unmodified
upstream flows passed. The consumer package adds five Redex-focused flows:
Regex/Filesystem/ProgramOptions APIs, mapped-file with a filtering stream,
isolated Boost.Atomic and Boost.DateTime compiled-component contracts, and the
Filesystem/Thread portability contract. All five consumers compiled and
executed successfully, covering 15 explicit assertions.

Both shared and static package modes passed for this exact recipe revision.
The shared package contains nine real libraries with stable SONAMEs, no
versioned symlink layout, and no path-bearing NEEDED entries. The static
package contains nine archives and no shared objects. Runnable artifacts pass
the signing and execution checks required by the package workflow. Results
from earlier 1.90.0.x candidates are historical only and are not reused as
1.91.0 evidence.

The exact validated references are:

- shared: `boost/1.91.0#09c6974457a6daf43d0ec183df8206e0:01d92cf349a0dd98ff915f4bd99a04430171517f#e3693530a4e917eba1d5ad14a28e4c28`
- static: `boost/1.91.0#09c6974457a6daf43d0ec183df8206e0:21b17f8b2bc0e9511e276e3d57a23893067cefe5#c80e29c36ad039c6b052e78f6104dbde`

## Tracking

- Dependency Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1247
- Downstream Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1092
- Pull request: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/3001
