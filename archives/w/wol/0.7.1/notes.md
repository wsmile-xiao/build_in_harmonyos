# HarmonyOS PC verification

- Board: `@tank_you` claimed `wol/0.7.1`, exact branch `feat/wol-0.7.1`, in the
  10-fire-seed competition activity. The board labels it C++, while upstream
  identifies the actual implementation as C.
- Official SourceForge `wol-0.7.1.tar.gz` is 445648 bytes, SHA-256
  `e0086c9b9811df2bdf763ec9016dfb1bcb7dba9fa6d7858725b0929069a12622`.
  The local archive and exact bytes transferred to the target matched. Target
  root: `/data/storage/el2/base/haps/entry/files/wol-0.7.1-20260926T200000`.
- Original 2004 `config.guess` failed on `uname -s = HarmonyOS` and
  `uname -m = aarch64`: `cannot guess build type`. The old `config.sub`
  rejected `aarch64-unknown-ohos`. The submitted `build_aux/config.sub` is
  based on GNU config project's 2026-05-17 file, reused from the earlier
  ProxSMTP adaptation. The original upstream file has SHA-256
  `f9a31e9a3f5b7cbeb8d8c3f2015895a51e7222130114c9c363fcbccd78e4bf6b`.
  The submitted copy adds only `exit 1` after the blank-OS error at line 2180,
  because upstream otherwise prints an error but accepts the malformed
  `aarch64-unknown--` input with status 0. The corrected submitted file has
  SHA-256 `35a8f04af0a3325d267fcf490ae3c6849c28fb20b53c7e1f6ac3d675fabfa9f2`.
  Explicit equal `--build` and `--host` values produced `cross compiling... no`
  in the final Conan log; target execution probes ran.
- The initial source build hit conflicting `getline`/`getdelim` declarations:
  `lib/getline.h` used `#if __GLIBC__ < 2`; musl leaves that macro undefined,
  so the obsolete `int` prototypes were enabled over musl's `ssize_t` system
  prototypes. The one-line patch requires actual glibc before this comparison.
  Configure also wrote `HAVE_ETHER_HOSTTON=0`; its fallback stub compiled but
  `ether.h` suppressed its prototype by checking definedness. The recipe's
  exact replacement checks the macro value. No upstream test case is changed.
- Native serial Clang build, `make check` consistency target and isolated
  `conan create` passed. Upstream `make check` contains no executable tests;
  it is not counted as an upstream test suite. Installed-package consumer
  test binds a UDP receiver to `127.0.0.1` and checks full 102-byte normal
  and 108-byte SecureON packets. Output:
  `WOL normal and SecureON loopback UDP payloads: PASS`.
  Final `create-v1.log` SHA-256:
  `c2807194b88a6663ffcdc7ad63c22e01fc533037fb6ce4682d2ec32682e569e0`;
  package revision `ff7d233274193ed728d509b133431279`.
- The final build still emits upstream legacy C warnings (old getopt and
  realloc prototypes, signedness and one format mismatch); no zero-warning
  claim is made. The packaged `wol-bootptab`/`wol-dhcpdconf` helper scripts
  were not independently exercised. No LAN broadcast, physical wake-up or
  target direct HTTPS download was verified. Conan verification temporarily
  used `file://` for the same SHA-256 official source; the committed recipe
  retains official HTTPS.
