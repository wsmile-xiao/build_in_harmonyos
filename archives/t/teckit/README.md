# teckit 2.5.13

HarmonyOS PC adaptation of TECkit. The recipe builds the engine and compiler
libraries directly with clang++, packages `teckit_compile`, `txtconv`, and
`sfconv`, and runs the untouched upstream `test/dotests.pl` regression suite on
the cross-built binaries.
