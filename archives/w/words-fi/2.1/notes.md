# words-fi 2.1 adaptation notes

The requested package identity and archive path are `words-fi/2.1`. The
immutable upstream input is GNU Aspell Finnish `0.7-0`, fetched from the
official GNU dictionary archive and checked against the pinned SHA-256 in
`conandata.yml`. The recipe, manifest, and source metadata keep the upstream
source version separate from the requested package version.

The recipe strictly decodes the prezip v2 `fi.cwl` source, strips Aspell
slash-suffix metadata, converts the ISO-8859-1 records to UTF-8, removes
normalization duplicates, and sorts by an ASCII-folded dictionary key followed
by the complete UTF-8 byte sequence. The architecture-independent output is
`share/dict/words-fi` with exactly 88,328 entries. The package retains both
upstream `Copyright` and `COPYING` files.

The upstream release ships no test target. All 19 package Python unit tests
passed. Five consumer scenarios passed: normal data validation, missing-file
rejection, the native non-HarmonyOS negative control, the HarmonyOS AArch64
device test, and the supplemental HarmonyOS x86_64 HDC test. The AArch64 device
reported `HARMONYOS_TEST_OK entries=88328 machine=aarch64` after compiling the
consumer with its HNP Clang.

On OpenHarmony 6.1.0.115/API 23 AArch64, Conan 2.29.1 passed G1-G4 recipe
verification and the consumer `test_package`. The repository `ohos-aarch64`
profile also passed the formal W3 `setup.sh` and `build_and_test.sh` flow:
1/1 package passed, with L0, L1, and L4 passing. L2 skipped because this is a
data-only package with no executable, and L5 reported no `bin/` or `lib/`
artifacts. The `finish` step generated `.ci-result.json` from the passing W3
run; its log hash is recorded there.

The full `finish` command returned 1 for checks outside Conan and W3: its clean
source check had no original source tarball in the temporary validation
snapshot, submit-readiness found no release packaging or staging marker, and
the repository-wide knowledge check reported existing empty fields in
E219/E253/E305. The package Conan verification and W3 gates themselves passed.

Direct HTTPS from the device timed out during the earlier isolated Conan run.
The official archive was staged only after checking its pinned SHA-256; the
later formal W3 run reused Conan's verified source cache. The committed recipe
and `conandata.yml` continue to use the official GNU HTTPS URL; no local source
URL is committed.
