# Legacy libc checks can select incompatible prototypes on musl

Status: knowledge-base extension candidate for maintainer review. This is a
tested portability pattern, not an assertion of automatic Path B scoring.

## Symptom and cause

The official WOL 0.7.1 source initially failed on HarmonyOS PC AArch64.
After allowing its 2004 Autotools script to recognize an explicit native
OHOS triple, Clang reported conflicting `getline` and `getdelim` types:
the bundled `lib/getline.h` declared them returning `int`, while musl's
`stdio.h` declares `ssize_t`.

The guard was `#if __GLIBC__ < 2`. Under musl, `__GLIBC__` is undefined;
preprocessing an undefined identifier in `#if` treats it as zero, so the old
glibc branch becomes true. This is distinct from using a glibc-private `stat`
constant: the failing mechanism is a false conditional selecting conflicting
function prototypes. The exact fix is
`#if defined(__GLIBC__) && __GLIBC__ < 2`.

A second nearby guard used `#if !defined(HAVE_ETHER_HOSTTON)` while configure
defined `HAVE_ETHER_HOSTTON` to `0`. The fallback implementation built, but
its prototype was omitted, causing an implicit declaration warning. The
recipe changes that guard to `#if !HAVE_ETHER_HOSTTON`; its final build no
longer emits that warning. This is the same broader failure mode: treating
macro presence as equivalent to a true capability value.

## Reusable approach

1. Read the actual generated `config.h`, system header and compiler error,
   not only `configure`'s yes/no output. For an old Autotools script, use a
   trusted, hash-pinned `config.sub` and explicit build/host identity; verify
   `cross compiling... no` if a native runtime test is claimed.
2. Audit guards involving implementation-specific macros. Require
   `defined(__GLIBC__)` before numeric comparisons, and test the value of
   configure-generated `HAVE_*` macros when they are explicitly 0/1.
3. Keep the source patch minimal, build from the official unchanged archive,
   and validate the installed binary's behavior. For this network tool, a
   loopback UDP receiver compares the complete Magic Packet bytes without
   broadcasting or waking a real machine.

## Evidence and boundaries

- Official source SHA-256:
  `e0086c9b9811df2bdf763ec9016dfb1bcb7dba9fa6d7858725b0929069a12622`.
  Target root: `/data/storage/el2/base/haps/entry/files/wol-0.7.1-20260926T200000`.
- Original configure log records `cannot guess build type`; first compiled
  source records conflicting prototypes. Final isolated Conan create log SHA:
  `c2807194b88a6663ffcdc7ad63c22e01fc533037fb6ce4682d2ec32682e569e0`.
  It reports native configure, a built installed package and normal plus
  SecureON 102/108-byte loopback UDP packet checks passing.
- Earlier ProxSMTP knowledge covers obsolete `config.sub`/platform detection,
  and an existing `stat` entry covers glibc-private constants. This proposal
  adds the distinct preprocessor false-branch and 0/1 capability-guard
  mechanisms. If a maintainer finds an earlier equivalent entry, merge it.
- Upstream `make check` has zero executable cases here. Legacy warnings
  remain. Broadcast, actual wake-up, helper scripts and direct HTTPS fetch
  on the target were not verified.
