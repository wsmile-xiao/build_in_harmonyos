# abcmidi 20260609 adaptation notes

## Source selection

The task-board version is `20260609`.  Upstream has no `2026.06.09` tag.
This package is pinned to upstream tag `2026.06.06`, commit
`b6571ab0de5e985fe28f4fa6aa6d657b8f89dfa1`, which is the latest release tag
before the task date.  Its GitHub archive SHA256 is recorded in
`conandata.yml`. The source URL uses GitHub's official codeload archive CDN;
it resolves to the same tag archive and SHA256 as the GitHub tag URL.

## Build and dependencies

The current upstream release provides a CMake build with eight executables:
`abc2midi`, `abc2abc`, `midi2abc`, `midistats`, `mftext`, `yaps`, `midicopy`,
and `abcmatch`.  It has no external Conan requirements and links only the
system math library.  Go is not used.

## Verification status

On OpenHarmony 6.1.0.115 aarch64, Conan 2.29.1 and clang 15.0.4 completed
`preflight_check.sh`, `conan-verify`, and `build_and_test.sh`. The upstream
CTest suite passed 19/19 tests. The test package converted ABC to MIDI and
asserted the `MThd` header, then converted the result back to ABC and asserted
the `X:` and `K:` fields.
