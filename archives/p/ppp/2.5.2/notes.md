# ppp 2.5.2 adaptation notes

Tracking issue: `#2118`

Branch/worktree:

```text
feat/ppp-2.5.2-2118
D:\harmonyos\worktrees\ppp
```

## W0 dependency result

The complete OHOS dependency graph resolves to `openssl/3.5.6`, recipe
revision `748fc4deb56588d6f8ce900b21e8eb0a`, with the published OHOS package ID
`6b129b068851896169fae42d399fa922d239ce8a`.

The GitHub tag snapshot was evaluated first, but it lacks generated Autotools
files. Using it would introduce `autoconf -> m4`, and `m4/1.4.19` has no OHOS
binary in the current graph. The official Samba release tarball includes
`configure`, `config.guess` and `config.sub`, so the final recipe avoids that
unavailable build-tool chain. No additional dependency adaptation is required.

## Source and build analysis

- Official release: 2.5.2, published 2024-12-31.
- Source URL: `https://download.samba.org/pub/ppp/ppp-2.5.2.tar.gz`.
- SHA-256: `47da358de54a10cb10bf6ff2cf9b1c03c0d3555518f6182e8f701b8e55733cb2`.
- The release contains generated `configure`, `config.guess` and `config.sub`.
- The recipe passes `--disable-maintainer-mode` so patched release-generated
  files are consumed directly instead of invoking unavailable target-side
  `aclocal`, Autoconf or Automake tools.
- Its unmodified `config.sub` rejects OHOS. Patch 0002 adds only the `ohos*`
  OS and `linux-ohos*` kernel/OS whitelist entries (E007).
- `aarch64-unknown-linux-ohos` then canonicalizes unchanged and produces
  `host_os=linux-ohos`, matching upstream's `linux*` branch.
- Plugins stay enabled. External libatm, PAM, PCAP, SRP, systemd and
  multilink/TDB integrations are disabled; PPPoATM uses the upstream built-in
  ATM address parser fallback.

The old archive reported an `__packed` conflict in `linux/if_pppox.h` but did
not include a reproducible build log. Patch 0001 carries a narrow E163 fix at
all three include sites (PPPoE and PPPoL2TP) and leaves the SDK headers
untouched. The shadow CI result remains the source of truth.

Official CI build `#25952` confirmed that maintainer mode is disabled and
compiled the core daemon and tools. It then exposed ambiguous zero-context
hunks in patches 0001 and 0003: CI's `patch-ng` placed cleanup directives
before the guarded UAPI include. Both patches now use context-bearing hunks,
and all seven patches replay in order with CI's `patch-ng` 1.19.1. Official
build `#25972` on `OpenHarmonyPCDeveloper-CI-007` then completed the build,
upstream tests, packaging and `test_package`; L0 and L1 passed.

The source patches use capability checks rather than an OS platform branch:

- patch 0001 supplies `__packed` only when the Linux UAPI environment has not
  defined it;
- patches 0001 and 0003 scope the socket-name workaround to Linux targets whose
  libc does not define `__GLIBC__`;
- patch 0004 uses Autoconf probes for `getspnam()` and `endspent()`; and
- patch 0005 inserts its logger inside upstream's visible
  `#ifdef UNIT_TEST_MSCRYPTO` block, while patch 0007 is bounded by an exact
  informational-option allowlist.

## Test plan

`build()` runs upstream `make -j1 check`. With the selected features the
expected test programs are:

1. `utest_crypto`
2. `utest_utils`
3. `utest_chap`
4. `utest_pppcrypt`
5. `utest_peap`

`test_package` asserts that five commands and the PPPoE plugin were installed,
then is designed to validate the exact `pppd --version` result, the upstream
`--help` usage surface, and a negative control proving that a missing explicitly
requested options file still fails through normal option processing. These nine checks
perform no privileged PPP link, route, serial-device or network operation.

## OHOS shadow CI result

The single-package heavy shadow run passed on 2026-08-13. The first successful
evidence snapshot was:

```text
commit: 85927cc84399fe8ba4563f0b0c3346d27a0591ff
outer: /storage/Users/currentUser/ohos-test-runs/codex-ppp-2.5.2-issue-2118-shadow-ci-r14-20260813-152656-28756
child: /storage/Users/currentUser/ohpc-ci-shadow/runs/85927cc84399-20260813T072658Z-run-28852
completed_at: 2026-08-13T07:31:43Z
```

Results:

- `make -j1 check`: 5 total, 5 passed, 0 failed, 0 skipped.
- `conan create`: passed; all five commands and the PPPoE plugin were packaged.
- `test_package`: passed and printed `pppd version 2.5.2`.
- Gates: L0, L1 and L5 passed; overall shadow status was `pass`.
- L2 skipped because its generic version/help probe is not applicable to all
  PPP commands. It is not the explicit test package gate.
- The r14 L4 warning identified `sprintf` in the TMPDIR unit-test patch. The
  patch now uses bounded `snprintf`; the package-local scan passes and the final
  snapshot rerun verifies the same gate.

The reproducible in-repository command remains:

```sh
CI_PACKAGES="archives/p/ppp/2.5.2" zsh ci/conan/build_and_test.sh
```

## Path B knowledge contribution

The draft
`knowledge/drafts/E325-draft-C0DX-privileged-daemon-informational-probe`
captures a reusable fail-closed contract for system daemons that load mandatory
global configuration before parsing side-effect-free informational options.
The recommended adaptation recognizes only an exact, single informational
argument before configuration, delegates output and exit behavior to the
upstream parser, and leaves all operational arguments on the original path.

The consumer test verifies both positive information surfaces (`--version` and
`--help`) and a negative operational-path control (`file <missing>`). This
distinguishes a narrow control-flow reorder from a broad configuration bypass
or a hard-coded version stub.

This draft does not duplicate E214, which addresses an interactive shell read,
or E246, which diagnoses SIGSYS after a restricted syscall. E091 and E163 cover
compile/link header conflicts rather than pre-configuration CLI dispatch.

## Path B submission scope

This submission requests Path A basic adaptation and Path B knowledge review.
The Linux PPP/PPPoX ABI, `/dev/ppp`, privileged network operations, Linux
headers and missing shadow-password APIs remain documented only as the source
event and runtime boundary behind E325; they are not a separate classification
claim.

The auditable mapping from the observed failure to patch 0007, the installed
consumer checks and the reusable draft is in
`reports/knowledge-contribution-evidence.md`. Final acceptance of E325 remains
a knowledge reviewer decision.

## Submission metadata

The package is a CLI tool, so R38 expects `archives/p/ppp/commands.json`.
The software-level declaration is present with `type=tool`, version `2.5.2`
and the binary-package flag; official builds `#25882` and `#25952` both passed
the R38 schema gate.
