# opusfile 0.12 knowledge expansion and classification evidence

## Purpose

This report records the evidence for classifying the opusfile 0.12 adaptation
as `【知识库扩展】`. It binds the accompanying E256 draft to the observed failure
and separates that new knowledge from issues already covered by the repository.

## Upstream and package scope

- Official source: `https://downloads.xiph.org/releases/opus/opusfile-0.12.tar.gz`
- SHA-256: `118d8601c12dd6a44f52423e68ca9083cc9f2bfe72da7a8c1acb22a80ae3550b`
- Build system: Autotools/Libtool.
- Deliverables: `libopusfile` and `libopusurl`, with HTTP/HTTPS support retained.
- Published Conan dependencies: `libogg/1.3.5`, `opus/1.5.2.1`, and
  `openssl/3.5.6`.

No upstream decoder, URL, seeking, TLS, or codec implementation is replaced.
The recipe adapts the existing upstream build and packaging contract.

## New reusable knowledge: E256

The preserved native OHOS r13 log contains this sequence:

```text
opusfile/0.12: RUN: ".../src/configure" ...
/system/bin/sh: .../src/configure: Permission denied
ERROR: ... autotools.configure()
ConanException: Error 126 while executing
```

Conan emits the source `configure` path as the first process.
`CONFIG_SHELL` affects shells started after Autoconf begins, so it cannot wrap
that initial launch. The reusable correction is to branch on
`settings_build.os == "OHOS"`, run `/system/bin/sh` with the official configure
path and `autotools._configure_args`, and retain `autotools.configure()` for all
other build executors.

This is the single subject of E256. The entry deliberately excludes unrelated
later failures and package-specific policy.

## Existing knowledge reused

- E007 covers the bundled GNU `config.guess`/`config.sub` triplet recognition.
- E011/E129 cover the later Autoconf temporary-directory permission failure.
- E087/E165 cover general script execution and interpreter-path problems on
  the target filesystem.

The recipe's platform patches and branch conditions are therefore a combination
of reused knowledge plus the narrowly defined E256 gap.

## Classification basis

- All three third-party dependencies are already published for the target
  profile; no private toolchain or unpublished dependency chain is required.
- The official release archive contains the complete source and a conventional
  Autotools/Libtool build.
- The triplet and filesystem failures follow existing repository patterns.
- Producing two libraries and describing two Conan components is normal package
  metadata work; it does not change upstream core behavior.
- The generated Ogg Opus fixture is a complete installed-package consumer, but
  it uses public libogg, libopus, opusfile, and opusurl APIs rather than adding a
  new runtime or test framework.
- Shared/static repetitions are build variants of one consumer and are not
  inflated into separate test cases.

These facts support Path A plus Path B: a conventional package adaptation plus
one narrowly scoped, reusable build-system knowledge addition.

## Validation boundary

The official source tree registers no upstream test entry (`0/0`). The added
consumer is one independent integration flow. Local cross builds created shared
and static AArch64 packages and compiled/linked the consumer; target execution
remains `NOT_RUN` and is not reported as a runtime pass.

The old PR HEAD `2297b849a331c68d28ab5940f722bad066d85c10` passed Buildbot build
11688 with matching `ci_pr_number=3159` and full `ci_revision`. That result is
historical evidence only. The classification update requires a new full-SHA
Review and Buildbot result before the PR can be submitted for review.
