# proxy-libintl 0.5 adaptation notes

## Scope

- Official tag: `0.5`.
- Official commit: `33934de09af6a6627eb44e310a8079df009abdbb`.
- Source SHA-256:
  `f7a1cbd7579baaf575c66f9d99fb6295e9b0684a28b095967cfda17857595303`.
- Downstream: GLib 2.84.0, which pins this exact source in
  `subprojects/proxy-libintl.wrap` when the target C library does not provide
  `ngettext`.

## Dependency boundary

The library has no third-party build or runtime dependencies in `STUB_ONLY`
mode. It provides the gettext-compatible `intl` dependency required by GLib
without fetching a Meson fallback during the GLib build.

## Platform adaptation

The package defaults to a static library. OHOS rejects `shared=True` because
the platform already provides a shared library named `libintl`; installing a
second `libintl.so` would create an ambiguous runtime dependency and violate
the repository's system-library isolation rule. Non-OHOS consumers may still
request upstream's shared build explicitly. Static builds propagate the
upstream `G_INTL_STATIC_COMPILATION` public definition so consumers do not
request DLL import symbols.

The OHOS CI profile declares absolute C and C++ compilers but not `ar` or
`ranlib`. Python-spawned Meson cannot reliably resolve the corresponding LLVM
tools by a bare name. The recipe therefore prefers explicit Conan archiver
entries, otherwise derives version-matched `llvm-ar` and `llvm-ranlib` from
the absolute C compiler directory, verifies both files, and injects them into
the generated Meson machine file. Missing tools fail configuration instead of
falling back to runner-only environment variables.

## Test accounting

Upstream 0.5 contains no registered test entry or test source. The adapted
package adds one installed-package consumer. It checks singular and plural
translation fallback, default and assigned domains, bind directory behavior,
and codeset behavior in one process. These checks are not separate tests.

An isolated Windows host `conan create` passed the same consumer flow `1/1`
for both static and shared packages. The OHOS `shared=True` negative check was
rejected before build as required. Fresh OHOS/aarch64 execution passed the
static installed-package consumer `1/1`; the eight internal checks remain one
logical flow. The acceptance runner does not export `AR` or `RANLIB`, so the
target build exercises the recipe's standard Conan-to-Meson tool binding.
