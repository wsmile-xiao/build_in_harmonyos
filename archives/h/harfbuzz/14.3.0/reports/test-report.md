# HarfBuzz 14.3.0 Test Report

Status: PASS for the accepted W3 snapshot; finish/Pre-PR remain pending.

## Counted test inventory

| Scope | Inventory | Executed | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: | ---: |
| Official upstream Meson entries | 75 | 75 | 75 | 0 | 0 |
| Added Conan consumer flow | 1 | 1 | 1 | 0 | 0 |
| **Counted tests** | **76** | **76** | **76** | **0** | **0** |

The consumer contains nine API/result assertions; assertions are not counted
as separate tests. Package inventory and signing checks are package gates, not
additional test cases.

## Upstream inventory

Meson introspection registered 29 `src` entries, one release-notes entry, 43
fuzzing chunks, and two thread/slow entries. The exact ordered list is in
`upstream-test-inventory.txt`. The original `testlog.json` is JSONL; strict
replay required 75 unique names in introspection order, result `OK`, return code
0, and one text terminal with `Ok: 75` and `Fail: 0`.

No upstream test source was modified or excluded. The recipe only binds the
Python interpreter and materializes signed shared-library aliases before the
unmodified Meson test command.

## Consumer inventory

The one C consumer links `harfbuzz::harfbuzz` from the shared package and
checks:

1. buffer allocation;
2. runtime version at least 14.3.0;
3. UTF-8 shaping of `Harmony`;
4. seven glyph records and matching info/position arrays;
5. the 14.3.x `hb_ot_fetch_number` symbol and empty-face result.

Its terminal marker was
`harfbuzz 14.3.0 shaping and fetch APIs: PASS (7 glyphs)`.

## Exact-snapshot evidence

- Git HEAD: `5116ab2fa920e2224098e41804c00feb82c241ca`
- Git tree: `87b6df3b01e77a24ee423cc516666fe25139a42a`
- Base: `00a9e1d20557f23c0f1d775a29195b5e3328753d`
- Device: `currentUser@10.62.215.229:2222`
- Run ID: `20260819T010115Z`
- Input tar SHA-256: `1149e1797417415e21cecb6d68e1869b6e2f653c3640a63b3486a31a517eeb92`
- Result tar SHA-256: `010979c158a39760ba83aa23e4f7c27bb1c7f85be81c0827fa070491720941a1`
- Conan create log SHA-256: `5197041b49066a36ff270dc4128d86ca20670d5cb3afed8faa1744eb56678b3e`
- Collected result SHA-256: `edb87894926b00dcaf04e2c9455e35d79813f4ad6e8a8b53dbfdf0a6207d7937`
- HarfBuzz RREV/PID/PREV: `d95aa2283a886e19705accd5a38c7aa9` / `02e364f2d646dda8acabc40d95696553e6e53235` / `1ac65b51d4fb18288f6913c88114e961`

The package contains 63 files. All 15 `.so`, `.so.0`, and fully versioned
aliases for core/subset/raster/vector/gpu are ordinary files with identical
bytes within each family and signed AArch64 ELF content.

## Failure history boundary

r4 failed at Meson configure because `/usr/bin/env` was inaccessible. r5
executed 75 entries but ended 9 OK, 21 FAIL, 43 ERROR, and 2 SKIP because
shared-library aliases and signatures were absent. r6 completed the technical
run but its package validator falsely required graph-info `package_folder`;
that original FAIL is preserved. Only fresh r7 is accepted as W3 PASS.

No Conan/CNB artifact upload or `/release` was performed.
