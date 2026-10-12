# raku-log 0.3.1 HarmonyOS PC adaptation notes

## Upstream

- Repository: https://git.tyil.nl/raku/log
- Release: `v0.3.1`
- Source archive: https://git.tyil.nl/raku/log/snapshot/log-0.3.1.tar.gz
- SHA256: `7c5837fe116bcaa1710fc65ed7e2987272c1368c5e3943691fddaa638cf2b8dc`
- Language: Raku 6.d (`META6.json` declares `perl: 6.d`); this is not Perl 5.
- Upstream tests: none are present in the release archive or the v0.3.1 Git tag.
- The snapshot URL is the author's own forge distribution endpoint; a snapshot is
  not immutable by construction, so the pinned sha256 is authoritative.

## Package design

This distribution is a pure Raku module with three `.rakumod` files and no native build system. The Conan recipe packages those sources and metadata unchanged and declares `rakudo/2025.11` as a runtime dependency. Rakudo, NQP and MoarVM 2025.11 OHOS/aarch64 packages are already published in the `ohpcd` remote.

The recipe declares only `settings = "os", "arch"`: nothing is compiled, so the
artifact is fully determined by the platform and adding `compiler`/`build_type`
would only split one identical source package into meaningless variants.

## Validation

- Conan profile: `ci/conan/profiles/ohos-aarch64` (OHOS 6.0, armv8, clang 15).
- W3: `conan create archives/r/raku-log/0.3.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=raku-log/*` passed.
- Module consumer test: 6/6 TAP assertions passed (contiguous severity scale, role conformance, undefined shared-instance initial value, consumer implementation, callability of all eight log levels, documented `with $Log::instance` idiom).
- HarmonyOS-specific consumer test: 5/5 TAP assertions passed (OHOS kernel identification, HongMeng kernel release, aarch64, cache directory access, and UTF-8 create/readback round trip on HarmonyOS).
- Upstream suite: 0 files, not supplied upstream; no upstream tests were altered or omitted.

The test runner uses Python `subprocess.run` to launch the packaged Raku executable and provides the runtime module path, MoarVM shared-library path and `MVM_JIT_DISABLE=1` explicitly.

### Why the HarmonyOS test is platform-specific

Observed on the packaged runtime, `raku -e 'say $*KERNEL.name'` reports
`harmonyos` on the OHOS target, whereas the same expression on Linux reports
`linux`. The first three assertions of `test_ohos.raku` therefore cannot pass on a
generic Linux host, which is what makes the file genuinely OHOS-bound rather than a
renamed POSIX file round trip.

### Coverage gap: JIT path not exercised

`test_runner.py` pins `MVM_JIT_DISABLE=1`, so only the MoarVM interpreter path is
verified. The variable is deliberately not exported to consumers (it would degrade
unrelated packages through the shared runtime), so JIT-enabled execution on OHOS
remains untested.

## Upstream defect found while writing tests

`Log::Implementation` template-dispatch candidates delegate with
`$template.fmt(|@args)`. Raku's `Str.fmt` takes its first positional argument as
the format string, so the call does not provide sprintf semantics:

```
> 'value %d'.fmt(42)
Your printf-style directives specify 0 arguments, but 1 argument was supplied
```

`sprintf('value %d', 42)` returns `value 42` as expected. This is an upstream
defect; the affected path is intentionally not asserted, and upstream sources were
not modified. Recorded in `knowledge/drafts/E543-draft-DBC4.kv`.
---

**编译结束**: 2026-10-02 13:45
**最终状态**: built
