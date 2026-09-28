# wol/0.7.1 for HarmonyOS PC

WOL sends Wake-on-LAN UDP Magic Packets. This recipe builds the official
0.7.1 SourceForge release on HarmonyOS PC AArch64 with Clang and packages the
`wol` command, upstream helper scripts, manual and license.

The release's 2004 Autotools platform script cannot recognize HarmonyOS. A
hash-pinned GNU `config.sub` is included; configure uses an explicit native
`aarch64-unknown-ohos` build/host pair. A minimal source patch prevents a
glibc-specific legacy `getline` prototype from conflicting with musl's system
prototype. A second exact replacement makes the bundled `ether_hostton`
fallback prototype follow the value of `HAVE_ETHER_HOSTTON`.

The installed-package consumer sends normal and SecureON packets only to
`127.0.0.1` and compares every received byte. It does not wake a physical
device or validate broadcast network permissions. Upstream `make check` has
no executable cases, so no upstream pass count is claimed.
