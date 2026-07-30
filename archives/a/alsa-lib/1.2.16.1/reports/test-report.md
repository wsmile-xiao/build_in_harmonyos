# alsa-lib 1.2.16.1 target test report

## Status

A fresh Conan W3 r35 completed directly on the OpenHarmony PC target on
2026-07-23. Both shared and static package modes returned zero. The official
upstream entries and every independent consumer entry passed in both modes.
No host result contributes to the reported pass rate.

| Independent test class | Entries | Target executed | Target passed | Failed |
|---|---:|---:|---:|---:|
| Upstream Automake `TESTS` | 2 | 2 | 2 | 0 |
| Consumer behavior flows | 6 | 6 | 6 | 0 |
| Consumer component flows | 2 | 2 | 2 | 0 |
| Consumer package workflows | 3 | 3 | 3 | 0 |
| **Logical total** | **13** | **13** | **13** | **0** |

Target pass rate: **13/13 (100%)**. Shared/static executions validate two
artifact modes of the same 13 logical entries and are not added together.
Timeout, unexecuted, unknown, and non-PASS terminal counts are all zero.

## Upstream boundary

`test/lsb/Makefile.am` registers exactly `config` and `midi_event`. Their
sources, inputs, and Automake terminal rules are unchanged. Each mode produced
exactly two `.trs` files, and every file contained only:

```text
:test-result: PASS
:global-test-result: PASS
:recheck: no
:copy-in-global-log: no
```

The root `test/Makefile.am` declares 19 `check_PROGRAMS`, but none is registered
in `TESTS`; they remain build-only evidence. The shared mode linked all 19.
The static mode linked 18 and intentionally omitted `oldapi`, whose source
requests `snd_pcm_hw_params_get_access@ALSA_0.9`, a shared-library symbol
version that a static archive cannot provide. This does not remove or alter
either registered upstream test.

The 60 public ABI probes only take function addresses. They are compile/link
evidence and are not counted as tests.

## Target evidence

Run directory: `alsa-lib-1.2.16.1-conan-w3-r35`

| Artifact | SHA256 |
|---|---|
| Frozen recipe input | `17dde268ec49738b2328000619068923d8c4f5659e531b26b056a9f4a78278ec` |
| Device runner | `3409e512c1b3d8c8e5e3188373399264d986c14d601db4dafcab64594811d2d2` |
| Shared `conan create` log | `7bcf227d5c6d936a065c6e390c4d8bfc8fe759eec1966307e370b539dbedcc77` |
| Static `conan create` log | `e7f1a23611ee476156a48cfff10377c93393f29799ce433ae0c0eac916b5578b` |
| Terminal status | `dbe01b69a45c0d23fbeec4d91d4c12a54be508d25ba3bae934274fd3cfbaf636` |
| Downloaded evidence bundle | `cfe65995eec2d3912c967cbf0036976f44bd8b4ddecca26d8481870c788e2e75` |

The evidence bundle contains both raw Conan logs, both exit files, the two
upstream `.trs` files per mode, the 11 exact consumer IDs per mode, consumer
signing rows, package signing manifests, ELF headers/dynamic sections, static
archives, effective profile, tool versions, and a remote SHA256 closure.

`validate_conan_w3_r35_evidence.py` rechecked the remote input identities,
driver and mode exits, exact terminal set, unique upstream PASS terminals,
all 11 consumer IDs and PASS lines per mode, signing-row uniqueness, and every
downloaded file hash. Its final result was:

```text
ALSA_W3_R35_EVIDENCE=PASS upstream=2/2 consumer=11/11 modes=2
```

This report does not claim a CI or artifact-publication result.
