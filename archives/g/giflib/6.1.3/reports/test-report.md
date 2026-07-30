# giflib 6.1.3 HarmonyOS target validation

## Environment

- Date: 2026-07-20
- Platform: HarmonyOS PC, AArch64
- Profile: `os=OHOS`, `os.version=6.0`, `arch=armv8`, Release
- Toolchain: clang 15.0.4, Python 3.12.9, Conan 2.29.1
- Input SHA256: `3eef2189a6431d9c37239975fafffd6bfa27ed642a5116a82aae30046b358edd`
- Isolation: previously absent target root and Conan home

## Machine summary

| Metric | Count | Evidence |
|---|---:|---|
| 总测试数 | 54 | 51 upstream entries plus 3 public-API consumers |
| 通过 PASS | 54 | Every logical case passed |
| 失败 FAIL | 0 | No failing logical case |
| 跳过 SKIP | 0 | No skipped logical case |

## Test classification

| Scope | Classification | Logical cases | Result |
|---|---|---:|---:|
| Upstream utility and codec regression entries | Integration/regression | 51 | 51/51 PASS |
| Public API encode/decode round trip | Integration | 1 | 1/1 PASS |
| Encoder operation-error ownership | Integration | 1 | 1/1 PASS |
| Truncated decoder error ownership | Integration | 1 | 1/1 PASS |
| Total | All | 54 | 54/54 PASS |

The upstream `tests/makefile` emits 51 TAP entries with distinct utility,
fixture, or regression failure boundaries. The three added consumers are
separate executable invocations with separate input and exit status. Internal
conditions are not split into more cases.

### Upstream 51-entry breakdown

| Make target | Count | Independent input or oracle |
|---|---:|---|
| `render-regress` | 8 | Eight different GIF fixtures decoded and compared with their RGB golden files |
| `gif2rgb-regress` | 1 | Fixed `gifgrid.rgb` encode/dump idempotency oracle |
| `gifbuild-regress` | 3 | Basic dump, icon idempotency, and animation idempotency |
| `gifclrmp-regress` | 8 | Eight fixture-specific color-map comparisons |
| `gifecho-regress` | 1 | Fixed `foobar` generation and dump comparison |
| `giffilter-regress` | 8 | Eight fixture-specific filter/decode comparisons |
| `giffix-regress` | 1 | One GIF truncated by exactly 20 bytes, repaired and compared |
| `gifinto-regress` | 1 | One compound TAP boundary for valid creation and invalid-input non-creation |
| `gifsponge-regress` | 8 | Eight fixture-specific sponge/decode comparisons |
| `giftext-regress` | 8 | Eight fixture-specific text dump comparisons |
| `giftool-regress` | 3 | Copy, deinterlace, and interlace golden comparisons |
| `gifwedge-regress` | 1 | Generated wedge compared with its fixed golden GIF |
| Total | 51 | Five 8-fixture groups (40) plus eleven other entries |

The fixed eight-file vector is `fire.gif`, `gifgrid.gif`, `porsche.gif`,
`solid2.gif`, `treescap-interlaced.gif`, `treescap.gif`, `welcome2.gif`, and
`x-trans.gif`. Every comparison helper emits its own named `ok` or `not ok`
line, and `tapview` makes any failing entry fail the enclosing command.

The 76 check count is `51 + 15 + 5 + 5`: one result per upstream TAP entry,
fifteen conditions in the round-trip workflow, five in the encoder failure
workflow, and five in the truncated-decoder workflow. It is not reported as
76 independent tests.

## Commands

```bash
W3_ROOT=/storage/Users/currentUser/tmp/codex-contest-validation/20260720/giflib-6.1.3-conan-w3-v2
export CONAN_HOME="$W3_ROOT/conan-home"

conan create archives/g/giflib/6.1.3 -nr \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  -o 'giflib/*:shared=True' --build='giflib/*'

conan create archives/g/giflib/6.1.3 -nr \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  -o 'giflib/*:shared=False' --build='giflib/*'
```

Both commands returned 0. Each mode reported `51 tests, 0 failures.` followed
by all three consumer PASS lines. Shared/static are packaging-mode reruns and
are not added together.

## Artifact audit

- Shared package: three real, byte-identical files named `libgif.so`,
  `libgif.so.7`, and `libgif.so.7.2.0`.
- Every shared file is AArch64, has SONAME `libgif.so.7`, and contains exactly
  one `.codesign` section.
- Shared file SHA256:
  `019f209b5f47e868505105719218bb42de27f9ac9dfaa836d77ddcce68da486e`.
- Static package: one non-empty `libgif.a`, SHA256
  `03843726541d7a8bdc48204391daf63f3d60a1c4d73cfde8ea69c0e0215b3b95`.

## Logs

- Shared: 296 physical lines, SHA256
  `101fe1299918effdaeed589dfcb1465c797c1c189245291f27c592334d0f03de`.
- Static: 284 physical lines, SHA256
  `bf37dfe59f39380ed1c010d738cdb4253cf62ee2dc3172f3af2778315d4b5086`.
- ELF header: SHA256
  `521e8aea002020161c529a97a19a043f3cc956a5867158d1af002c60c381f8fd`.
- ELF dynamic section: SHA256
  `d6cd26760ab93cfe02810aaedbc3c74680934463c4083b2ed83906775d9c7423`.
- ELF sections: SHA256
  `859da93e466732568ada88aaf895f8e8e9b2aee42364ad96d111d26ebe89476c`.
