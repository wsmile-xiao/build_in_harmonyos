# GLib 2.88.3 OpenHarmony PC Test Report

> Test date: 2026-08-27
> Target: OpenHarmony PC aarch64, `10.62.148.108:2222`
> Scope: complete upstream Meson inventory, package state test, and Conan consumer

## Summary

| Test set | Total | Passed | Failed | Skipped | Pass rate |
|----------|------:|-------:|-------:|--------:|----------:|
| Upstream Meson inventory | 363 | 363 | 0 | 0 | 100% |
| Added package state test | 1 | 1 | 0 | 0 | 100% |
| Added consumer program | 1 | 1 | 0 | 0 | 100% |
| **Independent cases** | **365** | **365** | **0** | **0** | **100%** |

The consumer program also passed 12/12 internal assertions. These assertions
are coverage metadata inside one program and are not counted as separate test
cases.

## Result

The exact frozen candidate completed one target transaction with 363/363
upstream entries, 1/1 state test, and 1/1 real consumer. The transaction used
one launch, one build job, and no GPU. It then completed two clean scans and
`POSTRELEASE_PASS`.

The post-W3 official finish r876 then passed `setup.sh`,
`build_and_test.sh`, and its generated `.ci-result.json` check for
`glib/2.88.3`. The aggregate finish return code remains 1 because of later
repository-level steps, so the truthful aggregate state is
`PARTIAL_POST_W3`; the official build/test substep itself passed.

Capability-dependent branches remain visible in the upstream inventory. The
successful run had no failed or skipped outer test entry. Source and patches
do not use an OHOS-named conditional macro. Historical failed or unconsumed
transactions are diagnostic only and are not included in these denominators.

## Evidence

- HEAD: `fdf98cd7a11119f65d90edae600c73d7ee0e94ee`
- HEAD tree: `4d65f48243aeeffa9bd068e9c105b5f9d699fa82`
- Runtime candidate tree: `66982ee9c8e9ec23baf33bb238bf7c0f6be0ce60`
- W3 run: `glib-2.88.3-w3-transaction-r873`
- W3 input SHA-256: `6830589cf8bd96d1e5d097485027521d1f03c33f43e9c0be41f7daaf9039b1de`
- W3 result SHA-256: `b1847f14f65476dc8ac33575c8719db7e0e0850b274801f9b8dcbee6c5dad3d2`
- W3 receipt head: `89d9c8878d4357fe883533c5d001657965d93a402d47cb851e231e532b2c847b`
- W3 host result SHA-256: `3191f78de05253a334137b641f922cba9de66ca1fec3eefc1bfdc5c8290aa37b`
- Receipt count: 12
- Launch count: 1/1; second launch: not run
- Cleanup: two clean scans and `POSTRELEASE_PASS`
- Official finish run: `r876`
- Official `.ci-result.json` SHA-256: `fd857e0f93d25892e4b08b013e65b9b6f88dd55b85fa4a6aaf054e8baa54e000`
- Official W3 local-CI log SHA-256: `f812be937f460de1511ab945d9f2f3bfded0cb1d88075e52fec678182bcf19a3`
- Official finish result SHA-256: `25713e7163254db5be0f18a455c83e38b9933db0e0b3b04f9c1bc28b7fc627af`
- Official finish device release: two clean scans for `/data/storage/el1/base/g2f876`

## Environment

```text
Package: glib/2.88.3
Conan: 2.29.1 OpenHarmony adaptation
Build parallelism: 1
GPU: disabled
Device host key: SHA256:I+zQ42EzfPJ37VXp0g9f8pYL+Xl+ndUZmr4/2ImQt98
```
