# GCC

GNU Compiler Collection package for HarmonyOS PC. Version 9.5.0 is a
minimal native AArch64 C compiler build: it intentionally excludes C++,
bootstrap stages, multilib, sanitizers, OpenMP, quadmath and Graphite/ISL to
fit the package CI while retaining real compile, link and execution tests.

The recipe uses only GNU/GCC official source archives. No GitHub source is
used. HarmonyOS CI validation remains pending until the official worker runs.
