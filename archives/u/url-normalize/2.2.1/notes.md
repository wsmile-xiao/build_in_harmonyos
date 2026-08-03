# url-normalize 2.2.1 adaptation notes

## Build environment

- Build system: PEP 517 / setuptools, pure Python
- Build date: 2026-07-30
- Compiler: N/A
- Status: built

## Source audit

- Upstream repository: https://github.com/niksite/url-normalize
- Tag: `v2.2.1`
- Tag commit: `918b135085d73f2a0441048ee01643c60fc7d89a`
- Official tag archive SHA256:
  `74b63f229012755bf85bc97a7e2c45df8e0f903166604c34ae766d0207e1c5ad`
- The official tag archive contains all 16 upstream test modules and 199
  collected pytest cases.

## Runtime dependency

- Upstream declares `idna>=3.3`.
- The OHPCD Conan remote has no `idna/*` recipe, so there is no published
  Conan dependency that can be referenced under R36.
- This recipe instead makes the Python artifact self-contained with the
  official `idna 3.15` PyPI sdist. Version 3.15 satisfies the upstream range,
  retains Python 3.8 support, and is the fixed release for
  GHSA-65pc-fj4g-8rjx / CVE-2026-45409 (`idna<3.15` is affected).
- Official idna sdist SHA256:
  `ca962446ea538f7092a95e057da437618e886f4d349216d2b1e294abfdb65fdc`.
- Independent verification against the PyPI 3.15 JSON and a fresh in-memory
  download confirmed the URL, 199245-byte size, SHA256, `Requires-Python
  >=3.8`, and BSD-3-Clause license. PyPI's current 3.15 vulnerability list was
  empty at verification time; that is not a guarantee about future findings.

## Packaging

1. Download and verify the official url-normalize tag archive.
2. Download and verify the official idna 3.15 source distribution.
3. Install pinned PEP 517 backends (`flit_core 3.12.0`,
   `setuptools 75.3.2`, and `wheel 0.45.1`) into an isolated build-only
   directory. idna 3.15 requires `flit_core>=3.11,<5` because its metadata
   uses the PEP 639 `license` and `license-files` fields.
4. Install both sources without dependency resolution or build isolation into
   the isolated Conan build tree.
5. Run the complete upstream pytest suite against that installed tree.
6. Copy both modules and their distribution metadata into
   `lib/python/site-packages`.
7. Copy url-normalize's MIT license and bundled idna's BSD-3-Clause license
   into the Conan package; the recipe declares both licenses.

The package intentionally exposes the Python library and module CLI
(`python3 -m url_normalize.cli`) without installing a `bin/` launcher.
Consequently it remains a library artifact and does not require a
software-level `commands.json`.

## Test evidence

- Official-source audit on WSL / Python 3.10.20:
  - pytest 9.1.1
  - pytest-cov 6.2.1
  - coverage 7.8.0
  - pytest-socket 0.8.0
  - upstream suite: `199/199` passed
  - measured upstream coverage: 99%
  - 178 non-fatal deprecation warnings report that idna has removed
    transitional UTS #46 processing; url-normalize 2.2.1 still passes the
    complete suite and idna says the argument will be removed in a future
    version
- Conan 2.29.1 / OHOS aarch64 WSL profile simulation:
  - the repository `ci/conan/build_and_test.sh` W3 pipeline was run against an
    isolated staging copy so its automatic mirror rewrite could not alter the
    committed official-only `conandata.yml`
  - upstream suite: `199/199` passed
  - packaged consumer: `26/26` assertions passed
  - W3: L0 PASS, L1 PASS, L2 SKIP (no `bin/`), L4 PASS, L5 PASS
  - W3 result: 1 succeeded, 0 failed
  - W3 package reference:
    `url-normalize/2.2.1#8eaaa50d0dd80c223b5a3c01bbee89c8:da39a3ee5e6b4b0d3255bfef95601890afd80709#3a8a3919bc184be7691f7c06325c5474`
- The first W3 attempt exposed a WSL DrvFS pytest capture failure
  (`FileNotFoundError` while truncating the capture tempfile). Running the
  same build tree with `-s` collected and passed all 199 cases, so the recipe
  now disables only pytest output capture; no test is skipped.
- R34 was independently repeated with both host and build profiles explicitly
  supplied. After the baseline `26/26` pass, the exact package `lib/`
  directory was moved aside; the consumer failed with
  `ModuleNotFoundError: No module named 'url_normalize'`. The directory was
  restored and the consumer passed `26/26` again. The W3 script's own
  single-profile negative command was not treated as sufficient evidence
  because this local Conan home has no default build profile.
- The consumer test validates distribution metadata, the bundled idna
  dependency, IDN conversion, path/port/query normalization, parameter
  filtering, default domain/scheme behavior, and the module CLI.
- Validation used the repository's local WSL OHOS profile simulation; physical
  HarmonyOS device execution was not applicable to this pure-Python library.

## Finish compatibility note

- The full `ohc-run.py finish` wrapper was not rerun for this audit fix. Its
  legacy G0 path previously attempted `/data/service/hnp/bin/bash` and a
  configure phase that this pure-Python v3 archive does not have; its source
  rewrite also nests proxy prefixes. The canonical W3 CI script, real
  `conan create`, upstream suite, consumer, and explicit R34 control were run
  instead. No generated infrastructure, summary, report, log, or marker files
  are included.

## Dependencies

- Runtime: Python 3.8 or newer.
- Conan package dependencies: none.
- Bundled Python dependency: idna 3.15.
- Build-only packaging tools: flit_core 3.12.0, setuptools 75.3.2,
  wheel 0.45.1.
- Build-only test dependencies: pytest 9.1.1, pytest-cov 6.2.1,
  coverage 7.8.0, pytest-socket 0.8.0. These versions remain compatible with
  the OHPCD worker's available coverage release.

---

**编译结束**: 2026-07-30 01:44
**最终状态**: built
