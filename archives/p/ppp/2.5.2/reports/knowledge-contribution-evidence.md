# ppp 2.5.2 Path B knowledge contribution evidence

## 1. Purpose and claim boundary

This document supports the Path B knowledge contribution for issue `#2118` and
PR `#5226`. It binds the observed ppp failure, patch 0007, test inventory,
device results, reusable E325 draft and remaining runtime boundary. The Linux
kernel and libc constraints below describe the source event and explain why the
consumer probe must remain narrow; they are not a separate classification
claim. Cross-compilation or `pppd --version` is not treated as proof of a live
PPP/PPPoE connection.

## 2. Upstream identity and scope

- Upstream: `https://github.com/ppp-project/ppp`
- Official release archive: `https://download.samba.org/pub/ppp/ppp-2.5.2.tar.gz`
- Source SHA-256: `47da358de54a10cb10bf6ff2cf9b1c03c0d3555518f6182e8f701b8e55733cb2`
- Build system: generated Autotools release, cross-compiled with Clang 15 for
  `aarch64-unknown-linux-ohos`
- Conan dependency: `openssl/3.5.6`
- Delivered commands: `pppd`, `chat`, `pppstats`, `pppdump`, and
  `pppoe-discovery`
- Representative delivered plugin: `lib/pppd/2.5.2/pppoe.so`

The Git tag snapshot was not selected because it requires regenerating the
Autotools files through an unavailable OHOS `m4` build-tool chain. The official
Samba release archive already contains `configure`, `config.guess` and
`config.sub`, avoiding an unrelated dependency adaptation.

## 3. Adaptation event and platform constraints

### 3.1 Linux kernel PPP and PPPoX coupling

A real session depends on the Linux PPP/PPPoX kernel ABI, `/dev/ppp`, privileged
ioctls, interface state, routes and network configuration. The upstream sources
directly include Linux networking headers and use Netlink/PPPoX structures.
HarmonyOS exposes enough compatible surface to compile the selected features,
but it does not provide an upstream abstraction that can replace these kernel
contracts or make a live connection an unprivileged operation.

This coupling is visible during compilation: the target Linux UAPI headers
conflict on `sockaddr_storage`, and `if_pppox.h` expects the `__packed`
declarator. Patches 0001 and 0003 use macro/libc capability checks, without
editing SDK headers or changing PPP protocol algorithms.

### 3.2 Build triplet recognition

The unmodified release `config.sub` rejects
`aarch64-unknown-linux-ohos`. Patch 0002 admits only the needed `ohos*` and
`linux-ohos*` forms. The canonical tuple remains unchanged and selects the
upstream Linux build path rather than inventing a new platform implementation.

### 3.3 libc account API gap

The upstream session code can call `getspnam()` and `endspent()` for shadow
password lookup. HarmonyOS libc does not provide those APIs even though the
header is present. Patch 0004 adds Autoconf function probes and enables the
optional lookup only when the header and both functions exist; it does not use
a platform macro or add a fake credential backend.

### 3.4 Test and deployment constraints

The standalone `utest_pppcrypt` expects GNU `error()`, and `utest_utils`
historically assumes writable temporary storage. Patches 0005 and 0006 provide
a logger protected by an explicit `UNIT_TEST_MSCRYPTO` guard and honor `TMPDIR`
using bounded `snprintf`, preserving all five upstream test programs and their
assertions. The production `pppd` preprocessing path therefore never defines
the added `error()` symbol.

Before deployment, `/etc/ppp` may be absent. Upstream `pppd` reads system PPP
configuration before answering informational options, which prevents a safe
package smoke test. Patch 0007 handles the exact long version/help options first
on every target; operational arguments still use the original configuration path.
The E325 draft generalizes the exact allowlist, upstream-parser reuse and
negative operational-path verification contract for other system daemons.

## 4. Patch-to-evidence matrix

| Patch | Obstacle | Scope | Verification |
|---|---|---|---|
| `0001-pppoe-define-packed-for-ohos.patch` | Linux UAPI packing/socket contracts | Context-bearing macro/libc guards at three PPPoE/PPPoL2TP include sites | all seven patches replay with `patch-ng` 1.19.1; official build `#25972` passes |
| `0002-config-sub-accept-linux-ohos.patch` | Release rejects OHOS triplet | `config.sub` whitelist only | tuple canonicalizes; configure completes |
| `0003-netlink-avoid-ohos-sockaddr-storage-redefinition.patch` | non-glibc Linux socket type conflict | Context-bearing libc guards in Netlink and pppstats users | `patch-ng` keeps both Netlink includes inside the guard; build `#25972` passes |
| `0004-session-disable-shadow-api-on-ohos.patch` | missing `getspnam`/`endspent` | Autoconf function probes plus compound `HAVE_*` guard | configure probes absent symbols; build and link pass in `#25972` |
| `0005-utest-pppcrypt-provide-ohos-error-stub.patch` | unresolved test logger | explicit `UNIT_TEST_MSCRYPTO` guard; absent from production preprocessing | production link and all five unit programs pass in `#25972` |
| `0006-utils-utest-respect-tmpdir.patch` | unwritable fixed temp location | test temporary path only | `utest_utils` passes on device |
| `0007-pppd-handle-info-options-before-system-config.patch` | version/help blocked by undeployed config | exact long-option allowlist without a platform branch | positive and fail-closed consumer checks pass in `#25972` |

Patch SHA-256 values:

```text
df181c60d9978c0b30f60ee14bf5870f41a9377480cc42098af5eb69b89dc2ca  0001-pppoe-define-packed-for-ohos.patch
78f710b43381d311528b85cb0a930d85c0609057c1d54c41980fc736ec8009a6  0002-config-sub-accept-linux-ohos.patch
4debd2111311945f17ea08e9d09a2d5452391bc9acb619166ab4ef9573b22d52  0003-netlink-avoid-ohos-sockaddr-storage-redefinition.patch
f7e9fbc7bb52c30f78fb14f16c376ac6377970e223523f13b17a769eb28d9459  0004-session-disable-shadow-api-on-ohos.patch
5ac9e0af36d0898e52bd9823dd0ce15a70e817db785a7ed26d1896586d03830f  0005-utest-pppcrypt-provide-ohos-error-stub.patch
f608830e42ef40951d7fecc787eeafd3b0d6b5dc36a6cd279b7b60e3a097e1f8  0006-utils-utest-respect-tmpdir.patch
408a31791c74485b28bd9b8a62c099b8d169c5658aa2edfaaf684aba5ee8051c  0007-pppd-handle-info-options-before-system-config.patch
```

## 5. Test inventory and results

The logical test count does not inflate shell checks or repeated CI runs:

| Scope | Independent checks | Result |
|---|---:|---:|
| Upstream `make -j1 check` programs | 5 | 5/5 pass |
| Installed commands present | 5 | 5/5 pass |
| PPPoE plugin present | 1 | 1/1 pass |
| `pppd --version` execution | 1 | 1/1 pass |
| `pppd --help` execution | 1 | 1/1 pass |
| Missing explicit options file negative control | 1 | 1/1 pass |
| Total | 14 | 14/14 pass |

The five upstream programs are `utest_crypto`, `utest_utils`, `utest_chap`,
`utest_pppcrypt`, and `utest_peap`. No test is deleted or skipped, and the two
test portability patches do not weaken assertions.

The first successful single-package device shadow evidence is:

```text
implementation snapshot: 85927cc84399fe8ba4563f0b0c3346d27a0591ff
outer: /storage/Users/currentUser/ohos-test-runs/codex-ppp-2.5.2-issue-2118-shadow-ci-r14-20260813-152656-28756
inner: /storage/Users/currentUser/ohpc-ci-shadow/runs/85927cc84399-20260813T072658Z-run-28852
completed_at: 2026-08-13T07:31:43Z
```

Final results recorded by the branch are L0, L1, L4 and L5 pass, one package
built successfully, `make check` 5/5, and `test_package` 7/7. L2 is skipped
because its generic probe is not valid for every command in the PPP suite. The
updated explicit consumer adds `--help` and a missing-options negative control;
both checks pass in official build `#25972`.

Earlier official PR CI passed three times:

- build `#23962`, worker `OpenHarmonyPCDeveloper-CI-033`
- build `#24029`, worker `OpenHarmonyPCDeveloper-CI-008`
- build `#24096`, worker `OpenHarmonyPCDeveloper-CI-016`

Builds `#23962` and `#24029` tested implementation commit
`a3d35ab0df960ed069265fa5c6400a4589531cd9`. Build `#24096` verified the
rebased documentation head `dd341c8a237d4afe6f4df9813b7c437cbbb66486`.
The current candidate replaces platform branches in five patches with macro,
libc, Autoconf-function, unit-test-build and argument-shape capability checks.
Official CI build `#25882` verified R38 metadata, all seven patch applications,
the generated configure script and the new shadow-function probes, then stopped
before C compilation when enabled maintainer rules invoked `aclocal-1.16`.
Build `#25952` verified the recipe fix (`maintainer-specific portions ... no`),
compiled `pppd`, `pppstats` and `pppdump`, and reached the PPPoE plugin. It then
showed that `patch-ng` had applied paired zero-context insertions from patch 0001
out of their intended order, removing the `__packed` and socket-name guards
before `linux/if_pppox.h`. Patches 0001 and 0003 now use context-bearing hunks;
an exact `patch-ng` 1.19.1 replay of all seven patches passes locally. Official
build `#25972` on `OpenHarmonyPCDeveloper-CI-007` then completed Conan create,
upstream `make -j1 check`, packaging and all nine consumer assertions. L0 and
L1 passed, giving 14/14 adapted checks with no skipped upstream test.

Builds `#25645`/`#25860` (CI-041/CI-008) lacked `libsqlite3.so.0`, and build
`#25951` (CI-029) lacked Python SSL support. They stopped in worker setup or
dependency resolution before the ppp build and are tracked as runner faults.
Inputs are fixed by these SHA-256 values:

```text
87753572034cc4e9485c412e2b90e55d3dbf300ee11cb3d9ec504f24c7759da0  conanfile.py
9a536944e796ffaf76db3ca94d7cc0151dead76adb6bd6949068ad9d971995bf  conandata.yml
d6e975310ecbead6933e73a7f4ac18fdd72a67f3d8ca4dc5f35c9eeb49a55aca  ../commands.json
f0ba6da31b2271b0285dd0b639533322af28c7204387674b98a2146a8e12f22d  test_package/conanfile.py
6ca0af3e013ba0c3bbb3d07e48a99b3012e5ee940a4c5c6c0c992406a0c9a961  test_package/test.sh
8d16e84fbb7c08bf7af64d2a0f8c3ad6e752ecef42355bd046cf0de2121ee2fe  test_package/MANIFEST.yml
```

## 6. Failure evolution and engineering choices

| Stage | Failure or risk | Root cause | Resolution and boundary |
|---|---|---|---|
| W0 source selection | Git tag needs unavailable OHOS `m4` graph | generated Autotools files absent | use checksum-pinned official release archive |
| configure | OHOS tuple rejected | old `config.sub` whitelist | narrow tuple patch; no generated-file rewriting at build time |
| build bootstrap | `make` invokes missing `aclocal-1.16` | patched `configure.ac` is newer while maintainer rules are enabled | pass upstream `--disable-maintainer-mode`; consume release-generated files without adding build dependencies |
| patch application | UAPI guards are removed before `if_pppox.h` | paired zero-context insertions are reordered by CI `patch-ng` | use context-bearing hunks and replay the complete ordered patch set with CI's parser |
| compile | packing and socket type conflicts | Linux headers combined differently by OHOS SDK | macro/libc capability checks; never modify SDK headers |
| link | shadow account symbols absent | HarmonyOS libc API gap | Autoconf probes gate optional shadow lookup |
| upstream tests | logger/temp assumptions fail | GNU API and fixed temp path assumptions | test-only logger and writable `TMPDIR`; preserve assertions |
| package smoke | version/help touch mandatory global config first | option order assumes deployed host | exact informational allowlist before config; negative control keeps operational arguments fail-closed |
| live connection | requires device, kernel and privilege | inherent PPP runtime model | do not run destructive network operations in shared CI |

## 7. Reproduction

From the repository root with the standard OHOS Conan environment:

```sh
CI_PACKAGES="archives/p/ppp/2.5.2" zsh ci/conan/build_and_test.sh
```

A valid result must include all five upstream tests, the five installed command
checks, the PPPoE plugin check, `pppd --version`, `pppd --help`, and rejection
of an explicitly missing options file. A host-only build or an unexecuted cross
binary must not be reported as the device result.

## 8. Path B knowledge contribution and deduplication

Candidate:
`knowledge/drafts/E325-draft-C0DX-privileged-daemon-informational-probe`.

The reusable contribution is not the generic suggestion to run `--version`.
It defines a control-flow and verification contract:

1. accept only one exact informational option before mandatory global config;
2. call the upstream parser/handler so output and exit semantics cannot drift;
3. leave mixed and operational arguments on the original configuration path;
4. verify version and help as separate information surfaces; and
5. include a negative operational-path check to detect broad bypasses.

Deduplication:

- E214 addresses shell `read` blocking non-interactive execution.
- E246 addresses SIGSYS/seccomp after a Linux-private syscall is attempted.
- E091 and E163 address header-level compile/link failures.

E325 instead addresses ordering between mandatory configuration loading and
pure CLI information dispatch in native system daemons. It complements those
entries. It is implemented by patch 0007 and the installed-package test; all
changed target behavior awaits current-head device or official CI.

## 9. Proven and unproven boundaries

Proven:

- official source identity and checksum;
- OHOS aarch64 configure, compile, link and package creation;
- all five selected upstream unit programs on the HarmonyOS device;
- command/plugin installation and `pppd --version` execution on the prior head;
- three successful official PR CI runs before the current capability-guard refactor.

Not proven:

- successful PPP or PPPoE negotiation with a peer;
- production authentication against shadow/PAM backends;
- route, DNS and interface lifecycle under a live privileged session;
- kernel PPP/PPPoX availability on every HarmonyOS PC image.

A live link test needs a disposable privileged target with `/dev/ppp`, known
peer fixtures and rollback of network state. Omitting that destructive probe
is an explicit validation boundary, not evidence that those capabilities pass.

## 10. Review request

Issue `#2118` and PR `#5226` request Path B knowledge review for E325. Reviewers
should assess novelty, reproducibility, the exact allowlist boundary, reuse of
the upstream handler, and the missing-config negative control. This submission
does not self-assign a score; final knowledge acceptance remains a reviewer
decision.
