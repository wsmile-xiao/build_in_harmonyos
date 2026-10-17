# DRAFT-ncmpc-libcpp15-cxx20-compat

Upstream C++23 Meson projects can be buildable on the OHOS clang 15 runner by
forcing the package to C++20 and patching the narrow libc++ 15 incompatibilities
that remain visible at compile time.

- Source event: ncmpc 0.53 HarmonyOS PC adaptation
- Trigger command: `conan create` with profile `ohos-aarch64`
- Affected phase: Meson configuration and C++ compilation

## Failure Chain

`ncmpc 0.53` declares C++23 in `meson.build`, but the device profile initially
forced C++17. That fails before reaching the real OHOS-specific incompatibility
surface because ncmpc uses `std::span`.

After setting the Conan package build to C++20, compilation reaches two libc++ 15
compatibility issues:

1. Runtime address accessors used `constexpr std::span` while returning a buffer
   built from `reinterpret_cast`. The OHOS clang/libc++ combination rejects this
   constexpr path.
2. `IntrusiveTreeSet` defaulted to `std::compare_three_way` for chrono
   `time_point` keys. The OHOS libc++ 15 path does not provide the upstream
   `time_point <=>` comparison needed by that default comparator.

## Minimal Fix

Keep the upstream project on C++20 for this package:

```python
def configure(self):
    self.settings.compiler.cppstd = "20"
```

Then patch only the rejected OHOS surface:

- Remove `constexpr` from the address-span accessors in `IPv4Address.hxx`,
  `IPv6Address.hxx`, and `InetAddress.hxx`.
- Add an explicit weak-order comparator for `Event::TimePoint` using `<` and
  `>` and pass it to `IntrusiveTreeSetOperators`.

The comparator shape used by ncmpc is:

```c++
struct CompareDue {
    std::weak_ordering operator()(const Event::TimePoint a,
                                  const Event::TimePoint b) const noexcept {
        if (a < b)
            return std::weak_ordering::less;
        if (a > b)
            return std::weak_ordering::greater;
        return std::weak_ordering::equivalent;
    }
};
```

This keeps the ordering semantics and avoids introducing platform macros into
upstream source.

## Why Not C++23

The package does not need the full C++23 standard library surface for the
validated build path. C++20 covers the `std::span` usage and is accepted by the
OHOS clang 15 worker. Forcing C++23 would make the recipe depend on a broader and
less stable standard library surface while still requiring the chrono comparator
patch.

## Verification Evidence

- With C++20 and the patches, shadow CI compiled all 115 Meson targets.
- The upstream `run_hscroll` smoke program executed.
- The installed CLI reported `ncmpc version: 0.53`.
- The version output included `wide`, confirming the `ncursesw` path remained
  enabled after the standard/library compatibility changes.
- CI metadata reported `L0=pass`, `L1=pass`, `L2=pass`, `L4=pass`, and
  `L5=pass`.

## B-Class Difficulty Evidence

This was not a single flag fix. The adaptation required sequencing the standard
level, Meson/pkg-config dependency discovery, Conan patch timing, and C++ library
surface patches. A premature C++17 or C++23 decision hides the actual source
compatibility issues and can lead to churn in unrelated dependencies.

## Do Not

- Do not lower the package to C++17 when upstream uses `std::span`.
- Do not globally patch the toolchain profile just for one application; keep the
  standard override in the package recipe.
- Do not replace the chrono ordering with integer casts or time-since-epoch
  shortcuts unless the upstream type semantics require it.
- Do not use `#ifdef __OHOS__` when a local, standard C++ comparator or
  non-constexpr declaration solves the problem cleanly.

## Related Entries

- E296: Meson cross files on OHOS need explicit machine-file binaries.
- E221: Application packages must verify their CLI contract with a consumer
  test.
- E077: Runtime `Operation not permitted` is separate from compile-time
  libc++ compatibility.
