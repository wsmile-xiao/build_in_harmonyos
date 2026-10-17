# libSM 1.2.6 W0 report

## Dependency graph

The official libSM 1.2.6 `configure.ac` requires `ice >= 1.1.0`, `xproto`, and
xtrans on the selected `--without-libuuid` path. Fresh target resolution used:

| Dependency | Recipe revision | Package revision | W0 disposition |
| --- | --- | --- | --- |
| libice/1.1.2 | `d8a6c94803be16b407b7403cc9d3b2ea` | locally built | Recipe taken byte-for-byte from `origin/main`; remote publication not claimed. |
| xorgproto/2025.1 | `f5274e33759da898a6e8d87d7708d47c` | `b7dc443b533634631c412ae235a57198` | Downloaded from `ohpcd`. |
| xtrans/1.6.0 | `664ea4b0b501c5f144fc094ab1a4dfc5` | `f07ea55c2b81548d01d94db631e0ac0e` | Downloaded from `ohpcd`. |

The graph permits a local build only for the merged libICE recipe. It does not
fall back to source builds for xorgproto or xtrans.

## Source identity

- Official URL: `https://xorg.freedesktop.org/archive/individual/lib/libSM-1.2.6.tar.xz`
- SHA-256: `be7c0abdb15cbfd29ac62573c1c82e877f9d4047ad15321e7ea97d1e43d835be`
- Upstream package version: `1.2.6`
- Selected activity: dependency, contrib task 3002, Issue #1889

## Platform inventory

The target was HarmonyOS HongMeng Kernel 1.12.0 on AArch64. The checked system
library roots contained no `libSM.so*`, so the recipe keeps its normal shared
default and validates both shared and static variants.
