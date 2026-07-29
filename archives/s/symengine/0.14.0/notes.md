# SymEngine 0.14.0 adaptation notes

## Configuration

- Build the static symbolic engine with GMP integer arithmetic.
- Use the bundled cereal and fast-float headers.
- Enable the upstream CTest suite for the GMP configuration.
- Disable benchmarks, LLVM, FLINT, MPFR, MPC, Piranha, OpenMP, and other optional accelerators.

## Verification

- The consumer test constructs and stringifies a symbolic addition expression.
- The package build registers and executes the 50 upstream tests applicable to
  the enabled GMP-only configuration.
- Python syntax, recipe structure, source SHA-256, and whitespace are checked locally.
- The official OHOS armv8 pipeline remains authoritative for the full build result.
