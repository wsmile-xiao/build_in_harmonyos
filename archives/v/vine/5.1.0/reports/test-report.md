# Vine 5.1.0 test report

## Fixed source and patch

- PyPI source: `vine-5.1.0.tar.gz`; SHA-256 `8b62e981d35c41049211cf62a0a1242d8c1ee9bd15bb196ce38aefd6799e61e0`.
- Patch: `0001-pytest-setup-method.patch`; SHA-256 `2e20d78cf2e1fd9f23bfcc3249206e75cf14e26712e45f49c7ef6c2f63721d76`.
- The patch changes only the barrier test fixture hook from nose-style `setup()` to pytest's `setup_method()`; it does not change runtime code or test assertions.

## Local upstream tests

The unmodified upstream suite had 38 passed and 4 failed because pytest 9 does not call the nose-style fixture hook. On the exact pinned source archive, the patch passed GNU patch `--fuzz=0` dry-run and application locally, then the upstream unit suite passed **42/42** on Python 3.11.0rc2 with pytest 9.0.2. This is local evidence only.

## OpenHarmony H1-004

- G0 `clean-verify`: **RC 1**. The source archive was extracted and the patch applied successfully; the next legacy `configure` step exited 127 because this 58-member pure-Python sdist has no root `configure` or `Makefile`. The log also contains a `getcwd` permission warning. G0 is not reported as passing. This framework flow assumes a configure/make project and does not match this package's supported Conan path.
- W3 candidate-scope CI: **RC 0**, using `prdiff` for the fixed 11 candidate paths. Conan setup/build passed and the OHOS `armv8` package consumers passed **6/6**.
- H1-004's Python 3.12.9 environment lacked pytest (`python3 -m pytest --version` returned RC 1, `No module named pytest`), so this run did not include the upstream 42 tests.
- Full `finish` and official PR CI were not run as part of H1-004.

## OpenHarmony H1 targeted pytest v2

- The exact patched source and private pinned pytest wheels were run once on H1. The independently rechecked raw archive is `evidence/h1-pytest-v2/vine-h1-pytest-v2-raw.tar.gz`, SHA-256 `f722bb6e17060535b8f493645a6df7e9c718a16f7c617472d629a41e31f3de1e`; its manifest is SHA-256 `8ee2e885732de93410a5254c7ae606ca54d08329408261aad183dceadea5f781`.
- `pytest.stdout` SHA-256 `284771bfefcd358e13f32ffe22f61b25427717a2bc3cb1b1f404090861830238` contains **42 passed in 0.30s**; `pytest.stderr` is empty (SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`). The 555 manifest entries were independently checked against the raw archive without mismatch; the patched fixture matches the expected H1-004 SHA.
- The outer runner returned **RC 1 after pytest finished**, when it attempted `python3 --version` while writing `result.json`; the bare executable lookup failed. `result.json` is absent, so the pytest subprocess exit code is **not persisted**. The H1 stdout records 42 passing tests, but this report does not claim a persisted pytest RC 0 or runner success.
- This evidence is separate from H1-004 Conan/W3 6/6. No Conan, W3, G0, `finish`, official CI, or push was performed in v2.

## Earlier H1-003 (superseded candidate)

H1-003 used the earlier long-context patch, so its G0 hunk failure is historical and is not evidence against the corrected H1-004 patch. Its Conan consumer 6/6 result is also superseded by the exact H1-004 W3 result above. The old W3 L1c text claiming upstream tests ran is unsupported by the recorded commands and is not counted.

## Remaining qualification and framework findings

The platform task is labeled `cpp`, while the pinned source is Python; the label is retained and eligibility is for official review. The required software-level README/manifest paths conflict with the framework's PF9 five-segment rule; both required files remain, with no preflight bypass. H1-003's `gen_summary` exception came from duplicate `knowledge_gained` keys in existing qpdf manifests; Vine did not modify framework files. No deprecated archive or staging marker was fabricated.

## Test inventory

| Test group | Count | Evidence |
|---|---:|---|
| Upstream unit tests | 42 | Local 42/42; H1 raw stdout reports 42 passed, but runner RC 1 and pytest subprocess RC was not persisted |
| Conan package consumer checks | 6 | H1-004 W3 6/6 on OpenHarmony aarch64 |
| HarmonyOS-specific API tests | 0 | No platform-specific API is used |