# acorn 8.17.0-ds-cs28.27.25

This is Debian's repackaged source for Acorn 8.17.0 and its component sources.
The Conan version normalizes Debian's `+ds+~cs28.27.25` syntax because the
Conan registry rejects that version syntax.

The upstream test runner loads 35 parser test suites through `npm run test`.
The consumer test invokes the packaged CLI, parses JavaScript, and validates
the JSON AST structure.

The initial HarmonyOS adaptation is restricted to armv8. On the validation
device, the upstream runner completed all 35 listed suites and the packaged
CLI AST smoke test passed 1/1. The recipe prefers the Harmonybrew Node/npm
toolchain because the device's hnp npm aborts during its native errno check.
