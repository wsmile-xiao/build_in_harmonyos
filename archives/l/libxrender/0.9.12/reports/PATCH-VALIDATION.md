# libxrender 0.9.12 portability validation

Date: 2026-08-19 (Asia/Hong_Kong)

## Inputs

- Official source SHA256:
  `b832128da48b39c8d608224481743403ad1691bf4e554e4be9c174df171d1b97`.
- `0001-config.sub.patch` SHA256:
  `052364bf9f664b9d223a9bca4b3ac44c4abe2a98ceeda73e74022c98c97a2ec7`.
- `0002-config.guess.patch` adds a narrow HarmonyOS/aarch64 branch before the
  existing `NetBSD` branch.
- `0002-config.guess.patch` SHA256:
  `28687518f5fb05eb391bfbf4131dfb65ce0cef7ea931f4e174e35f6c39ff5626`.
- The upstream generated `configure` file is not retained as a patch input.

## Directed checks

- Unmodified `config.sub aarch64-linux-ohos`: exit 1, OS not recognized.
- Patched `config.sub aarch64-linux-ohos`: exit 0 and
  `aarch64-unknown-linux-ohos`.
- Linux control `aarch64-unknown-linux-gnu`: unchanged and accepted.
- Invalid OS control: rejected.
- Patched `config.sub`: shell syntax accepted.
- Unmodified `config.guess` on HarmonyOS/aarch64: exit 1, system not recognized.
- Patched `config.guess` on HarmonyOS/aarch64: exit 0 and
  `aarch64-unknown-linux-ohos`.
- Patched `config.guess`: shell syntax accepted and non-aarch64 HarmonyOS
  machines are rejected.
- Exact Git patch check and replay for both patches: passed.
- The recipe's build-local `configure` derivation requires exactly two
  `umask 077` occurrences and replaces exactly those two with `umask 022`.
- The original source-tree `configure` remains byte-identical to upstream.
- Source and patch conditional-compilation macro scan containing `OHOS`: zero.

No build or target test is claimed by these directed checks.
