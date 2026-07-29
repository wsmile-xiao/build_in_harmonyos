# Opus 1.4 patch packaging equivalence

The target W3 r8 candidate contained three functional patches. Its candidate
manifest SHA-256 is
`496723fa7493e5206a2421b4e0a7029eaa5f1c4e3532dea49496e04dc102c204`.

The refreshed r9 candidate represents the same changes as nine patches with
nonblank unified-diff context. Its candidate manifest SHA-256 is
`f72ec9812f258fae032beb56979a2c5d50a86894f511df0f7564e41c6d4125d1`.

Validation results:

- all seven non-patch candidate inputs are byte-identical between r8 and r9;
- both candidates use the official source archive SHA-256
  `c9b32b4253be5ae63d1ff16eea06b94b5f0f2951b7a02aceef58e3a3ce49c51f`;
- standard `git apply --check` accepts all nine r9 patches in order;
- GNU patch dry-run and replay pass with `--fuzz=0`;
- Conan's patch-ng accepts all nine r9 patches in order;
- the patched r8 and r9 source trees contain the same 401 files with identical
  SHA-256 values.

The machine-readable result is
`E:/HarmonyPC/validation/opus-1.4/candidate-equivalence-r9.json`. Because the
effective source and every non-patch execution input are unchanged, the r8
target results remain the runtime evidence for this patch-packaging refresh.
