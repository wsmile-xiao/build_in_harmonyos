# alass 2.0.0 Path B candidate evidence

## 1. Claim boundary

Issue `#2224` is submitted as Path A plus a Path B knowledge-extension candidate. Final classification and scoring remain an official reviewer decision.

The Path B claim is not based on patch size, elapsed build time, the number of shadow CI attempts, Harmonybrew bootstrap, or serial Cargo compilation. It is based only on the reusable diagnosis and deterministic remediation of a legacy Rust Unix dependency lock graph that cannot compile for the modern OHOS target environment.

This submission does not claim Path C.

## 2. Original dependency boundary

- Upstream release: `v2.0.0`
- Build system: Rust 2018 Cargo workspace
- Workspace packages: `alass-core`, `alass-cli`
- Conan library dependencies: none
- Git dependencies: none
- Bundled C crate: `webrtc-vad 0.4.0`
- Original lock entries: `ctrlc 3.1.3`, `nix 0.14.1`, `libc 0.2.62`
- Target toolchain: Rust/Cargo 1.97.1 and clang 15.0.4 on `ohos-aarch64`

FFmpeg is optional runtime functionality for video references and is not needed for compilation or subtitle-to-subtitle validation.

## 3. Reproduced failure and root cause

The untouched lock graph reached Rust compilation but failed in old Unix portability crates:

1. `libc 0.2.62` produced 662 compile errors with the Rust 1.97 OHOS target configuration.
2. Updating only `libc` proved insufficient: `nix 0.14.1` still produced 45 ABI/type errors for `target_env=ohos`.
3. Linker selection alone could not fix crate source and cfg tables that predated OHOS support.

The direct dependency responsible for the old signal-handling graph is `ctrlc`. Its upstream manifest constraint permits a compatible 3.x update. Updating that smallest direct root lets Cargo resolve a modern, internally consistent `nix`/`libc` graph without changing alass source behavior.

## 4. Deterministic remediation

The portability patch updates the lock graph to:

| Package | Original | Patched |
|---|---:|---:|
| `ctrlc` | 3.1.3 | 3.5.2 |
| `nix` | 0.14.1 | 0.31.3 |
| `libc` | 0.2.62 | 0.2.189 |

Related transitive entries and checksums are committed in `patches/0001-update-rust-runtime-dependencies.patch`. The main recipe and `test_package` export byte-identical copies; their final SHA-256 is `3e4f503910c10519f0a31551e7d3acee98c4d954389682bdc53b2d06d9fa566b`.

The required invariants are:

1. Preserve upstream `Cargo.toml` semver constraints.
2. Update the smallest direct root dependency, not arbitrary transitive packages in isolation.
3. Export and review the complete deterministic `Cargo.lock` delta.
4. Build and test with `--locked` after applying the patch.
5. Keep registry caches task-local and never edit shared downloaded crate sources.
6. Verify both upstream behavior and the packaged consumer contract.

## 5. Validation matrix

| Configuration | Result | Evidence |
|---|---|---|
| Original `libc 0.2.62` graph | FAIL | 662 Rust compile errors |
| Newer libc with old `nix 0.14.1` | FAIL | 45 ABI/type errors |
| Modern bounded lock graph, direct build | PASS | locked release build completed |
| Modern bounded lock graph, direct upstream tests | PASS | 3/3 |
| Final Conan main recipe upstream tests | PASS | 3/3 |
| Final packaged consumer smoke | PASS | 5/5 |
| Fresh-source upstream suite in `test_package` | PASS | 3/3 |
| Destructive negative test | PASS | consumer test fails when package artifact is removed |

Final shadow CI run:

- Run ID: `codex-unknown-lib-alass-2.0.0-2224-r8-20260816-150649-14297`
- Exit code: 0
- L0/L1/L2/L4/L5: PASS
- Runner stderr: empty
- Device lock: released

## 6. Reusable knowledge and duplicate boundary

The proposed E327 draft applies to dormant Rust projects that pin old Unix portability crates and are later built with a modern OHOS-native Rust compiler. Its reusable decision path is:

```text
locked build fails inside old libc/nix
  -> identify the direct dependency that owns the Unix graph
  -> update that root within upstream semver constraints
  -> audit the complete lock delta
  -> retain --locked
  -> run upstream + consumer + negative tests
```

Existing repository experience already covers Harmonybrew `.real` wrappers and ETXTBSY mitigation. E327 deliberately excludes those topics and records only the lock-graph migration method.

## 7. Why this is not Path C

alass uses public Rust/Cargo/clang tooling and has a bounded test surface. It has no private HarmonyOS API, kernel ABI, assembly, JIT/W^X requirement, cross-architecture emulator, closed component, multi-daemon protocol test, or large mandatory Conan dependency chain. The final build takes minutes rather than requiring a special scheduler or an exceptionally large validation matrix.

The honest request is therefore Path B knowledge-extension review, not high-difficulty Path C classification.

## 8. Review request

Please review whether the following combination qualifies for Path B:

1. a reproduced two-stage failure showing why a one-package update is insufficient;
2. a semver-bounded, deterministic lock migration rather than an unbounded dependency refresh;
3. unchanged alass functional source and unchanged upstream tests;
4. locked main/fresh-source builds, 3/3 upstream tests, 5/5 consumer assertions, and destructive negative evidence;
5. a directly related, non-indexed E327 knowledge draft with explicit forbidden approaches.
