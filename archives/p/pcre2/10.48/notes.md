# PCRE2 10.48 OpenHarmony PC adaptation notes

## Scope

- Official source: PCRE2 10.48 release archive.
- Static PIC libraries: 8-bit, 16-bit, 32-bit, and POSIX wrapper.
- Tools: `pcre2grep`, `pcre2test`, and `pcre2-config`.
- JIT enabled and exercised by both the official suite and consumer tests.
- No third-party dependencies (zlib/bzip2 support explicitly disabled).

## Approach (reuse of proven 10.47 adaptation)

The 10.48 recipe is a version bump of the proven 10.47 recipe
(`archives/p/pcre2/10.47/conanfile.py`), which handles every known OHOS quirk:

1. **capability-tested shell probe** — HMDFS is noexec for extracted configure
   scripts; the recipe probes candidate shells with a clean `pwd` child-process
   check and rejects shells that corrupt the working directory.
2. **CONFIG_SHELL/SHELL reassertion after conanbuild** — Autoconf re-executes
   through CONFIG_SHELL even when another shell is passed explicitly.
3. **MKDIR_P=/system/bin/mkdir -p on OHOS** — Automake's noexec install-sh
   probe would otherwise fail during config.status dependency bootstrapping.
4. **LOG_COMPILER dispatcher** — interprets only the `RunTest`/`RunGrepTest`
   shell drivers; the compiled ELF tests keep direct execution; `make -j1 check`
   still produces one authoritative four-entry summary.
5. **Relocatable discovery metadata** — all four `.pc` files derive prefix from
   `pcfiledir`; `pcre2-config` derives prefix from its installed path; `.la`
   files removed.

## Portability patches (regenerated for 10.48 context)

1. `0001-config.guess.patch` — 10.48's bundled config.guess (2026-08) still has
   no HarmonyOS branch; adds `HarmonyOS|OpenHarmony) echo "$UNAME_MACHINE-unknown-linux-ohos"`.
2. `0002-config.sub.patch` — 10.48's config.sub still rejects
   `aarch64-linux-ohos`; adds `linux-ohos*` to maybe_os, `ohos*` to the basic OS
   list, and `linux-ohos*` to kernel-os validation.
3. `0003-configure-hmdfs-umask.patch` — 10.48's generated configure still uses
   `umask 077` for its temporary directory; changed both masks to `022` (fixes
   `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied`).

No source or patch uses an OHOS-named conditional compilation macro.

## Test inventory

Official `make -j1 check` registers four entries (same as 10.47):
`pcre2posix_test`, `pcre2_jit_test`, `RunTest`, `RunGrepTest`.

Local run (CI profile ohos-aarch64, `make -j1 check` inside `conan create`):
**4/4 passed**, SKIP=0, XFAIL=0, FAIL=0, ERROR=0.

Conan consumer (test_package): 8 flows — 8/16/32-bit API, POSIX API,
`pcre2grep` exact-line match, `pcre2test -C` config query, pkg-config static
link consumer, `pcre2-config` relocation, plus metadata relocation checks 6/6.
`pcre2test -C` confirms: PCRE2 10.48 2026-08-31, 8/16/32-bit, UTF/UCP
(Unicode 17.0.0), JIT (ARM-64, executable memory yes).

## Validation

`conan create` exit 0 with the CI profile:
`-pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
--user=ohpcd --channel=stable --build=missing`.

Network note: direct download from the official GitHub release URL timed out on
this worker (connect timeout to github.com); the recipe keeps the official URL
(R39). Local verification fetched the same official tarball via a mirror
(sha256 `ebcc25aa...` identical, verified against the committed conandata).
CI injects mirror fallbacks per framework policy.

## Path B knowledge contribution

No new draft in this PR. The 10.47 adaptation already submitted its reusable
knowledge (E330 capability-tested shell + LOG_COMPILER dispatch); 10.48 reuses
it unchanged. The toybox-ln long-option draft was contributed separately with
kmod/34 (PR #8333).
