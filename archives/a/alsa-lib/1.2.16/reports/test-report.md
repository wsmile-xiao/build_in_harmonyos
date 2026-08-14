# alsa-lib 1.2.16 target test report

## Status

A fresh Conan W3 completed directly on the OpenHarmony PC target on
2026-08-10 (shared mode, ohos-aarch64 profile). The official upstream entries
and every independent consumer entry passed. No host result contributes to the
reported pass rate.

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
in `TESTS`; they remain build-only evidence. Neither registered upstream test
is removed or modified.

## Recipe provenance

The 1.2.16 recipe is adapted from the existing 1.2.16.1 recipe: the seven
scoped portability patches apply to the 1.2.16 sources with the same semantics
(verified with `git apply --check`; only hunk line offsets differ). Official
archive SHA-256: `122b1e3166d55fe19bcde656535d7a36f2ab10e66c72c6ad2f43f20ffded0a96`.

## Local adaptation fix

The test package's relocated pkg-config consumer parses `-I`/`-L` flag paths
with a boundary scan (`_pkg_flag_paths`) instead of `shlex.split`, so build
workspaces whose path contains spaces (for example `build_in_harmonyos-main (1)`)
no longer break the relocated include/lib resolution check.
