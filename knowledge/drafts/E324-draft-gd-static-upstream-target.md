# E324 - CMake static upstream tests must link the real target

> Status: DRAFT | Source: gd 2.3.3.2 PR #3401 | Evidence commit:
> `f9ae7f760b376e3e64ebf5658bdda6b95e64c12b`

## Error Pattern

A CMake project can expose a different library name to upstream test helpers
than the target actually produced by a static-only build. In libgd 2.3.3,
`BUILD_SHARED_LIBS=OFF` with `BUILD_STATIC_LIBS=ON` creates the `gd_static`
target, but the upstream `gdTest` helper still used `gd` through `GD_LIB`.
During the HarmonyOS PC upstream-test build this degraded to a bare `-lgd`
link and failed before CTest could run.

## Reusable Remedy

Apply the fix only when upstream tests are explicitly enabled:

1. Keep the default package build path unchanged.
2. Patch upstream test configuration during source preparation for the test
   build, not in delivered headers or consumer code.
3. Make the test helper link the real CMake target produced by the selected
   static/shared variant. For libgd static tests this means assigning
   `GD_LIB` to `GD_LIB_STATIC`, so CMake preserves the target dependency and
   build ordering.
4. Run the native upstream CTest and the installed-package consumer separately.
5. Report only the exact native HarmonyOS PC passed/total counts.

The key rule is to keep CMake target identity intact. A test helper should
consume the target name that CMake created, rather than falling back to a
linker search name that may not exist in the build tree.

## Verified Evidence

PR #3401 moved the repository recipe directory to `gd/2.3.3.2` to avoid
overwriting the already published `gd/2.3.3` package while keeping the upstream
source release at libgd 2.3.3.

On HarmonyOS PC aarch64, commit
`f9ae7f760b376e3e64ebf5658bdda6b95e64c12b` completed:

```text
conan create archives/g/gd/2.3.3.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -o gd/*:with_upstream_tests=True --build=missing --build=gd/*
```

Results:

```text
Upstream CTest: 81/81
Installed consumer CTest: 1/1
```

The public PR body and Issue #2151 record the exact command, tested commit,
and evidence boundary. CI or host runs were not used to infer the test rates.

## Boundary

This draft does not justify changing upstream test expectations, skipping
tests, or publishing a rate from CI. It applies when the upstream test build
fails because a helper references a logical library name that no longer maps to
the actual CMake target under the chosen static/shared variant.

Do not apply the workaround to normal package builds unless the upstream
project also needs the target-name correction outside its test configuration.
