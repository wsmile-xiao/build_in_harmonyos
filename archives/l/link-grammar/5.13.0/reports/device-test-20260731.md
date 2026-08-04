# Link Grammar 5.13.0 HarmonyOS PC validation

## Environment

- Device: HarmonyOS PC test device
- Architecture: AArch64
- Conan: 2.29.1 OHOS build
- Compiler: OHOS SDK Clang 15.0.4
- Final run: `link-grammar-5.13.0-20260731-v16`
- Build isolation: new Conan home and package cache for v16

## Sources and dependencies

- Link Grammar tag archive SHA256:
  `a545b7efb7aceab2d8ad301466f199778a3da712928999ed8d66deb32ca3184f`
- GNU Autoconf Archive SHA256:
  `7bcd5d001916f3a50ed7436f4f700e3d2b1bade3ed803219c592d62502a57363`
- `pcre2/10.45` binary revision:
  `cf10e83f43cd9b8dd5dc5d21d4d44ab9`
- `sqlite3/3.49.1` binary revision:
  `9bae7e00509d3fd4c2f65da552f63fad`
- Build tools: `automake/1.18`, `libtool/2.5.4`, HNP Flex 2.6.4

Configure detected `libpcre2-8` and defined both `HAVE_PCRE2_H=1` and
`HAVE_SQLITE3=1`. The generated runtime feature summary contains no Conan
dependency path.

## Test results

The complete enabled upstream test inventory contains four programs. No
upstream test source was modified.

| Test | Result |
|------|--------|
| `dict-reopen` | PASS |
| `multi-dict` | PASS |
| `multi-thread` | PASS |
| `mem-leak` | PASS |

Upstream result: 4/4 passed, 0 failed, 0 skipped.

The added Conan consumer built and linked through the generated
`link-grammar::link-grammar` target. On the device it loaded the packaged
English dictionary, checked the exact version, parsed `This is a test.`, and
reported eight valid linkages.

The packaged `link-parser` also ran twice on the device:

1. `link-parser --version` reported `link-grammar-5.13.0`, `linux-ohos`, and
   `HAVE_PCRE2_H=1`.
2. Batch mode loaded `<package>/share/link-grammar/en/4.0.dict`, parsed the same
   sentence, and reported linkages.

Added consumer result: 2/2 passed.

## Artifact audit

- Package folder: 546 regular files, 25,561 KiB.
- `link-parser`: 64-bit LSB arm64 ELF; only `libc.so` is listed as NEEDED.
- Consumer executable: 64-bit LSB arm64 ELF.
- `liblink-grammar.a`: 66 members; zero nested `libsqlite3.a` or PCRE2
  archives.
- Packaged `.la` files: zero.
- RPATH/RUNPATH entries in `link-parser`: zero.
- `ohos-test-runs` path occurrences in `link-parser` and
  `liblink-grammar.a`: zero.

SHA256 values:

| Artifact | SHA256 |
|----------|--------|
| `link-parser` | `4b3dc72ea7b9da794a4ca0108a519ecb8c3c0c760c440d2abe7061ed0509cd8c` |
| `liblink-grammar.a` | `7cb4c034b47e97017ed37fa24a55169a33a2f94056e2fd5bf31d8c5428e89dcc` |
| `test_link_grammar` | `411bbc6264b4420d0481814c5a067a0d8d16388df4fe229b236d832497b38f56` |
| Full v16 log | `2659e1c1eb99608e4708b82cea60c096a4ea9f09bda7b527e268809aba99be7b` |

## Scope boundary

This report proves clean source build, package creation, full enabled upstream
tests, installed-package consumption, and CLI execution on one HarmonyOS PC.
It does not claim CI, merge, upload, or publication.
