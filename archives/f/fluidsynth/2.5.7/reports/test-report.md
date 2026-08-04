# FluidSynth 2.5.7 W3 test report

Date: 2026-08-01

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 33 | 100% |
| 通过 (PASS) | 33 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: 100%

## Frozen input

- Candidate: `candidate-w3-r8.tar.gz`
- Candidate archive SHA-256:
  `05ad834aef1b7c537fdd20cf251e729b6be724017c09d3064903933ba287688a`
- Candidate manifest SHA-256:
  `c2b97e238243c1232e8aad7477e076e808120b390ffed5141c44edb1448aa3dd`
- Target: HarmonyOS PC, aarch64
- Conan: 2.29.1
- Build parallelism: one job

The shared and static runs used the same frozen recipe, source archives,
profile, and test package. Metadata in this report was written only after both
runs reached a terminal state.

## Test accounting

FluidSynth registers 30 upstream tests in the selected portable configuration.
The installed-package test adds three logical consumers: a C++ CMake consumer,
a C pkg-config consumer, and the packaged `fluidsynth --version` command.

| Configuration | Upstream | Consumers | Logical result |
|---|---:|---:|---:|
| Shared | 30/30 | 3/3 | 33/33 |
| Static | 30/30 | 3/3 | 33/33 |

The project total is 33/33 logical tests. Running both configurations produced
66 successful configuration-level executions; this is not reported as 66
distinct test cases.

The pkg-config consumer intentionally opens a nonexistent SoundFont and checks
the documented failure path. FluidSynth therefore writes expected diagnostic
messages while the consumer itself exits successfully.

## Artifact gates

Shared:

- Upstream test ELF signing: 30/30
- Installed package ELF signing: 2/2
- Consumer ELF signing: 2/2
- Regular-file shared aliases: 2/2
- Packaged license files: 3/3
- Evidence archive SHA-256:
  `57befea76fd6036be67c3e963b8e96432141c40417a4454fdfbb32943e96195d`
- Conan log SHA-256:
  `a6beab54703654e117d1543a7239a5fce54c8f64d0c61a127692a48071d5ecae`

Static:

- Upstream test ELF signing: 30/30
- Installed package ELF signing: 1/1
- Consumer ELF signing: 2/2
- Static pkg-config private libraries: 3/3
- Packaged license files: 3/3
- Evidence archive SHA-256:
  `6bc99603242fba7443c6b6ab0cf16dc510df444ae8e896b0729bb11cc0e1c1d9`
- Conan log SHA-256:
  `57562aaf95f6a5be5a1f39c098c9bac25cec81c83a5c67b4ad6157dcc122d87a`

Both evidence archives passed their internal `evidence-manifest.tsv` checks
after transfer. Both terminal states record `conan_create_exit=0`,
`validation=PASS`, and `runner_exit=0` bound to the full candidate manifest
SHA-256 above.

An independent shared-package validator then rechecked the ABI and security
surface and reported `VALIDATION_FAILURES=0`. Its log SHA-256 is
`902c996ed9d45e47d3cc10deb0affd9b7ec9210ac335d8db3e604767bcbc639b`.

## Result

`W3_RESULT=pass`. The recipe is built and device-validated, but not yet
published; `commands.json.binary` therefore remains `false`.
