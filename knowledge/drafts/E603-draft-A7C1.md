# E603: Legacy target LINK_FLAGS can vanish from Conan CMake Ninja rules

## Scenario and symptom

A source patch can set `LINK_FLAGS "-Wl,-soname,..."` on a shared-library
target and configure without error, while the selected Conan CMakeToolchain and
Ninja build still omit the flag from the real shared-link command. The output
file can look correct even though `llvm-readobj --dynamic-table` reports no
`LoadName` and target consumers record a build-tree-relative NEEDED path.

## Root cause

Legacy `LINK_FLAGS` is a source-level property, but the effective build contract
is the generated link rule for the active configuration. In the observed
CMake 4.1.2/Ninja Release build, the property did not reach that rule. A generic
cache flag alone is also insufficient when the active configuration supplies a
configuration-specific shared-link flag. The recipe therefore has to bind both
the generic and active build-type cache variables. Separately, CMake's
`OUTPUT_NAME` and Conan's `cpp_info.libs` use the logical stem without the
conventional `lib` prefix; confusing the filename with that stem creates
`-lliblemon` when the actual link contract is `-llemon`.

## Reusable repair

1. Inject the required shared-link option with
   `CMakeToolchain.cache_variables` into both `CMAKE_SHARED_LINKER_FLAGS` and
   the active variant such as `CMAKE_SHARED_LINKER_FLAGS_RELEASE`.
2. Read back `CMakeCache.txt` and the exact `build.ninja` shared-link command;
   the source property alone is not evidence.
3. Inspect the built ELF dynamic table and the consumer's NEEDED entries before
   target execution.
4. Keep `OUTPUT_NAME` as the logical stem (`lemon`, not `liblemon`) so the
   generated file and Conan `cpp_info.libs` agree on `liblemon.so`/`-llemon`.
5. Apply the same SDK tool fallback to production and test-package signing;
   for an LLVM-only SDK, use `llvm-readobj --sections` when `readelf` is absent.

## Validation

Run-018 proved the source `LINK_FLAGS` text was present while the generated
Ninja link command and ELF SONAME were missing. The final liblemon 1.3.1
run-032 used one launch and passed 42/42
upstream CTest cases, 3/3 state checks, one Conan consumer with six assertions,
and the signed after probe.  The package contained `liblemon.so`, relocated
`LEMONConfig.cmake`, headers, pkg-config metadata and tools.  Frozen validation
and postrelease cleanup both passed.

## Safety and applicability boundary

Use recipe-wide shared-link flags only when their effect on every shared target
is intended. For multi-library builds, prefer `target_link_options` on the
exact target. Do not infer SONAME from the file name, accept a cache value
without generated-command readback, weaken target execution into a compile-only
check, or replay a consumed W3 run. Recipe, patch, binary, runner, or validator
changes require a newly frozen successor with fresh transfer and one launch.
