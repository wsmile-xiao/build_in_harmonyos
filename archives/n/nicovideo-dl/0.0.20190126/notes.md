# nicovideo-dl 0.0.20190126 adaptation notes

## Status

- Adaptation state: built by Windows-native Conan; HarmonyOS shadow pending
- Adaptation date: 2026-09-10
- Target: HarmonyOS PC aarch64
- Build system: custom single-file Python package

## Source audit

- Upstream project: https://osdn.net/projects/nicovideo-dl
- Public mirror/fork: https://github.com/hakatashi/nicovideo-dl
- Version source: Debian 0.0.20190126 orig archive
- License metadata: Debian identifies the bundled license as Expat; the
  additional no-promotion clause is represented as the SPDX X11 variant.
- Source URL:
  https://deb.debian.org/debian/pool/main/n/nicovideo-dl/nicovideo-dl_0.0.20190126.orig.tar.gz
- Source SHA256:
  886980d154953bc5ff5d44758f352ce34d814566a83ceb0b412b8d2d51f52197
- Archive contents: one executable Python 3 script, no tests, no setup.py,
  and no native build files.

## W0 dependency result

- Conan package dependencies: none.
- Runtime dependency: Python 3.
- Build dependency: Python 3.
- Test dependency: Python 3 standard library.
- Dependency split: not required.

## Build and packaging design

1. Download the fixed Debian orig archive and verify SHA256.
2. Run the source script with the active Python interpreter using `--version`
   and `--help` as deterministic source smoke checks.
3. Install the script as `bin/nicovideo-dl`.
4. Set executable permissions and install the embedded X11/Expat-derived
   license text.
5. Use the consumer test to exercise the installed package path, command
   discovery, version output, help output, and an offline invalid-input path.

`conandata.yml` records the authoritative Debian source archive and its
verified SHA256. The recipe reads this metadata through Conan's
`self.conan_data` interface.

## Upstream tests

The source archive has no upstream test target or test files. Therefore:

- Upstream tests collected: 0
- Upstream tests passed: 0
- Reason: the release is a single-file script archive without a test suite

The `test_package` tests are adaptation-owned consumer tests and are kept
offline. They do not claim to be upstream tests.

## Known compatibility note

Python 3.12 prints a deprecation warning for the upstream `cgi` import during
normal execution. The import and the CLI smoke checks pass on the current
local Python 3.12 interpreter. Python 3.13 execution should be verified in
shadow CI; replacing the removed `cgi.parse_qs` usage would be a separate
source patch if that runtime is selected.

## Local verification

- Source archive SHA256: passed.
- Source `python nicovideo-dl --version`: passed, output `2011.02.08`.
- Source `python nicovideo-dl --help`: passed.
- Windows native Conan 2.12.0 `conan create`: passed.
- Windows native test package: 8/8 executed assertions passed. The two PATH
  assertions are POSIX-only, so the HarmonyOS target total is 10 assertions.
- Conan package contents: `bin/nicovideo-dl` and `licenses/LICENSE` present.
- HarmonyOS PC device/shadow CI: not run; no device window was requested.

## Next shadow CI command

After Conan is available on the HarmonyOS PC worker, run:

```sh
conan create archives/n/nicovideo-dl/0.0.20190126 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

The expected Conan consumer test is the `test_package/test_nicovideo_dl.py`
script invoked by `test_package/conanfile.py`.

## Path B knowledge drafts

This PR adds two directly related knowledge-draft pairs:

- `knowledge/drafts/DRAFT-nicovideo-dl-script-cli-conan-runtime.kv`
  and `.md`: packaging and consumer-test rules for a single-file,
  extensionless Python CLI with no standard build metadata.
- `knowledge/drafts/DRAFT-nicovideo-dl-source-license-provenance.kv`
  and `.md`: provenance and license review rules when a historical release
  is recovered from a Debian `orig` archive.

Both are drafts only. They do not modify the formal knowledge graph or reserve
an `E###` identifier.
