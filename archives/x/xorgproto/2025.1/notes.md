# xorgproto 2025.1 adaptation notes

## Scope

- Dependency Issue: #1280.
- Downstream tasks: GraalVM #1085 and OpenJ9 #1084 through their X11/AWT dependency chains.
- Path: A (basic adaptation) + B (knowledge innovation). Knowledge draft E229
  captures the reusable compile-only test_package pattern, draft E230 captures the
  CI L0c source-suffix contract, and draft E231 captures generated public headers;
  all three drafts accompany this software PR for editor review and promotion
  that direct-copy recipes would otherwise omit.
- The points repository list has no `xorgproto` entry, so this dependency has
  one dependency Issue and no contest-claim Issue.

## Source and packaging

The official X.Org 2025.1 archive matches SHA256
`d6f89f65bafb8c9b735e0515882b8a1511e8e864dde5e9513e191629369f2256`.
The source tree contains 155 static public headers, while both upstream Meson
and Autotools also generate and install `X11/Xpoll.h`. That header substitutes
the target libc's `fd_set.fds_bits` or `fd_set.__fds_bits` member. The recipe
therefore probes both members with the C compiler declared by the Conan profile,
generates the 156th header, and retains OS, architecture, and compiler in the
package ID while dropping only build type. Generated `.pc` files use
`${pcfiledir}/../..` and remain relocatable in the Conan cache.

The historical 2024.1 archive contains only manifest/notes and two Autotools
patches; it has no Conan recipe or test package. Those patches are not carried
forward because the 2025.1 recipe does not execute Autotools and therefore does
not consume `config.guess` or `config.sub`.

## Tests

Upstream defines one `evdev-keysym-check` entry. On the initial host it exits
77 because Python `libevdev` is unavailable; this is the script's explicit SKIP
contract, not a passing test.

The archive contains 155 static public `.h` files, plus generated `Xpoll.h`.
Each selected header is compiled independently with the OpenHarmony SDK 12
compiler and sysroot. Exactly 83 compile cleanly as
standalone C11 consumers under `-Werror`; 71 require an upstream-prescribed
include order. The remaining two, `recordstr.h` and `xf86vmstr.h`, deliberately
emit upstream `#warning` diagnostics because they are obsolete compatibility
headers, so they are not counted as passing `-Werror` consumers. The test
package generates one source and one object per selected header using the
compiler from the Conan profile. These are distinct public-header inputs with
independent compile failure boundaries, not split assertions or repeated
shared/static builds.

The `Xpoll.h` consumer explicitly expands `descriptor_set.__X_FDS_BITS`, so a
wrong probe result cannot pass as an include-only smoke test. One additional
package-metadata workflow verifies that all 29 installed `.pc` modules exist
and contain relocatable `prefix` and `includedir` values. The adapted test total
is therefore 84 real workflows. The fresh HarmonyOS PC rerun after the W4 fix
used a new remote directory and Conan home, selected `fd_set.fds_bits`, packaged
156 headers, and passed all 83 header consumers plus the metadata workflow. The
upstream keysym check remains separate and its documented exit-77 SKIP is never
reported as a pass.

The target PC has no `cmake` executable, so the previous CMake-based consumer
could not run despite the package itself building successfully. E229 records
the reusable fix: for compile-only header consumers, read the C compiler from
Conan's `tools.build:compiler_executables` configuration, fail if it is absent,
and invoke it directly without a shell `CC` fallback. This keeps the test tied
to the same profile as CI while avoiding an unnecessary CMake dependency.

The first independent W4 also found that `header_smoke.c.in` was invisible to
CI L0c, which accepts only files ending in `.c`, `.cpp`, `.cc`, `.cxx`, `.sh`,
or `.py` within `test_package/`. The substantive template was renamed to
`header_smoke.c`, and `exports_sources`, the manifest, and the contest body were
updated together. A second fresh HarmonyOS create passed after that rename.
E230 records both the suffix rule and the prohibition on empty marker files.

A later independent W4 compared the direct-copy recipe with the upstream Meson
and Autotools install definitions and found that `Xpoll.h.in` is configured into
an installed public header. Copying only source-tree `*.h` files silently omitted
it and made the all-settings-cleared package ID invalid. E231 records the general
fix: inventory generated install outputs, reproduce the target compiler probe,
package the generated header, retain settings that affect its content, and add
a consumer that expands the generated ABI-sensitive token.
