# xorgproto 2025.1 test report

## Environment

- Target: HarmonyOS PC, `os=OHOS`, `arch=armv8`, Release profile.
- Compiler: Clang 15 from `tools.build:compiler_executables`.
- Source: official X.Org `xorgproto-2025.1.tar.gz`.
- Source SHA256: `d6f89f65bafb8c9b735e0515882b8a1511e8e864dde5e9513e191629369f2256`.
- Conan: 2.29.1.

## Test counts

| Scope | Classification | Count | Result |
|---|---:|---:|---:|
| Upstream `evdev-keysym-check` | Other | 1 | 0 PASS / 1 SKIP (exit 77) |
| Independent public-header consumers | Unit/component | 83 | 83 PASS |
| Relocatable pkg-config package workflow | Integration | 1 | 1 PASS |
| Adapted workflows | Total | 84 | 84 PASS |

The 83 header cases use distinct public headers, source files, object files,
and compiler failure boundaries. They are not repeated shared/static runs or
split assertions. The metadata workflow validates all 29 installed `.pc`
modules. The test package therefore records 112 top-level assertions: 83
non-empty objects plus 29 module records. The `X11/Xpoll.h` consumer expands
the compiler-probed `fd_set` member instead of merely including the header.

`recordstr.h` and `xf86vmstr.h` are intentionally obsolete compatibility
headers that emit upstream `#warning` diagnostics. They are excluded from the
passing `-Werror` list rather than weakening the compiler gate.

## Commands

```bash
python3 -m py_compile \
  archives/x/xorgproto/2025.1/conanfile.py \
  archives/x/xorgproto/2025.1/test_package/conanfile.py

conan create archives/x/xorgproto/2025.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build='*'
```

The final command ran in a new remote directory with a new Conan home and
returned exit code 0 after the generated-header fix. Its key output was:

```text
generated Xpoll.h with fd_set.fds_bits
package(): Packaged 156 '.h' files
package(): Packaged 11 '.txt' files
package(): Packaged 29 '.pc' files
validated 29 relocatable pkg-config modules
validated 83 independent public-header compile outputs
```

The generated `X11/Xpoll.h` contains `#define __X_FDS_BITS fds_bits`, matching
the successful target compiler probe. The raw final log SHA256 is
`640FE40CB7B696D4FD1DE3BCE3E03A37B2819F6EE412DC2BAC1C560EA5E668B5`.
