# kbd-bkeymaps 2.8.0 port notes

## Scope

This is a data package. It builds the Kbd 2.8.0 `loadkeys` converter on the HarmonyOS AArch64 device, invokes `loadkeys -u -b` for each distributed `data/keymaps/i386/**/*.map`, compresses the resulting BusyBox binary maps deterministically, and installs them under `share/bkeymaps/<layout>/`. The temporary converter is not included in the Conan package.

The 201 upstream source maps are preserved. When two source subdirectories contain the same map basename, one canonical path is selected by a stable layout priority and the alternate map is retained with its source layout appended to the filename.

## HarmonyOS adaptation

- The recipe is restricted to `os=OHOS`, `arch=armv8`; these maps contain native-endian key-table payloads.
- `TMPDIR` is set to a writable Conan generator directory because HarmonyOS device `/tmp` may not permit the temporary-directory mode used by Autoconf.
- Autoconf runs with `/system/bin/sh`: the bundled HNP Bash cannot resolve its current directory on the device's `/storage` mount.
- The release's GNU `config.guess` predates HarmonyOS detection; a small source patch returns its native `aarch64-unknown-ohos` tuple, which the bundled `config.sub` accepts.
- Kbd's loadkeys and common diagnostics reference glibc-only `program_invocation_short_name`; a package-local helper retains the executable name on glibc and reports `loadkeys` on HarmonyOS.
- The temporary converter uses `loadkeys -u -b` so Unicode keysyms are serialized independently of the build device's console mode; the default 8-bit conversion rejects valid upstream Unicode layouts on a headless build device.
- Kbd 2.8.0's Unicode converter cannot encode the `Meta_PageUp` symbol in `data/keymaps/i386/neo/3l.map` and would silently emit an empty key entry. The recipe maps that one unsupported symbol to `PageUp`, preserving the navigation key action in the generated binary map.
- The build target is limited to `src/loadkeys`; unrelated Kbd utilities and virtual-console operations are not packaged.
- Flex 2.6.4 and Bison 3.8.2 are build requirements. There are no runtime dependencies.

## Upstream test inventory

Kbd 2.8.0 has 101 Autotest cases: 46 library unit cases (`libkeymap` 29, `libkbdfile` 14, `libcommon` 3), 50 end-to-end cases, and 5 utility cases. The full upstream suite was run against the official 2.8.0 source with this package's two patches: all 101 tests passed (0 failed, 0 skipped). It was run as root through upstream `tests/check.sh` on Ubuntu 24.04 x86_64 in a KVM-backed QEMU guest with VGA and `/dev/tty60`; `SANDBOX=priviliged`, `HAVE_VGA=1`, and an empty `CHECK_KEYWORDS` enabled every registered test. The build used `--datadir=<tests>/data --disable-compress` so the tools read the upstream test fixtures, and the setfont test font was verified on the virtual console before the suite. Ubuntu's strace 6.8 rejects the legacy syscall-filter syntax in Kbd's unchanged `tests/strace.sh`, so a temporary wrapper translated only `trace=/open.*/,/ioctl` to the equivalent strace 6.8 syntax `trace=/open.*,ioctl`; no upstream test source or assertion was changed. The package-specific HarmonyOS Conan test also validates the complete generated map set.

## Verification

`test_package/test_bkeymaps.py` decompresses and structurally parses every installed map, checks the BusyBox signature/table lengths, verifies the full keymap set and canonical `us/us.bmap.gz`, and checks both HarmonyOS identity and AArch64 architecture when Conan is running with the OHOS profile.

The targeted repository CI and Conan 2.29.1 run passed on a HarmonyOS 6.0 AArch64 device with the `ohos-aarch64` profile. Conan built the converter, generated and packaged all 201 maps, and ran the consumer test successfully (`validated 201 bkeymaps; OHOS AArch64 check=enabled`). CI reported L0, L1, and L4 as passing. L2 was skipped because this data-only package installs no executable; L5 reported a warning because it installs no `bin/` or `lib/` artifacts.
