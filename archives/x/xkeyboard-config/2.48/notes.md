# xkeyboard-config 2.48 adaptation notes

## Source and scope

The official X.Org archive is
`https://xorg.freedesktop.org/archive/individual/data/xkeyboard-config/xkeyboard-config-2.48.tar.xz`.
Its 953316 bytes match SHA-256
`b77041324f0109f77161ee43743fe04baa485866af8460d31e476ad3f7648fd5`, also
recorded in the Debian source metadata. The archive contains pure XKB data and
generators, not a target ELF library, so no Conan runtime dependency is needed.

## Build behavior

Meson generates the `base` and `evdev` rules, compatibility symbols, XML/LST
catalogs, the versioned XKB root, and the legacy X11 alias. The recipe passes an
explicit target prefix of `/`; this is required when Conan runs Meson on
Windows, where the helper can otherwise emit a drive-qualified `F:/` prefix.
NLS remains enabled so the upstream locale catalogs are not silently omitted.

## Validation

The upstream pytest suite and `verify-group-names.sh` are executed with the
official source tree, generated rules, private xkbcomp/xsltproc tools, and the
system libxkbcommon runtime. The Conan consumer is source-bound through
`test_package/source_inventory.json`: it verifies each data-domain inventory,
parses all four generated rules XML files, checks the two aliases, and rejects
absolute pkg-config prefixes.

## Safety boundary

The package contains data and metadata only. Consumer success does not replace
the target W3 run; target execution must still use the current package identity,
fresh transfer/readback, and a single device launch before platform submission.
---

**编译结束**: 2026-09-07 03:32
**最终状态**: built
