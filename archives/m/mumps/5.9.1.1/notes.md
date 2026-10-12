# MUMPS 5.9.1.1: real parallel repair

Upstream identity is MUMPS 5.9.1; `.1` is an adaptation repair, not an upstream release.
The already published recipe hardcodes libseq and installs fake MPI headers. This repair
uses one published MPICH C/Fortran ABI, ScaLAPACK and OpenBLAS, retaining all four arithmetics.

## Source changes

Five original save/restore examples select MUMPS_SAVE_DIR with bounded length checks.
The absence of the environment variable preserves `/tmp`; invalid/truncated values fail.
Original calls, fixture matrices, test IDs and numerical expectations are unchanged.
These changes must be frozen using the official refresh-patch --auto generator.

## Evidence boundary

Native r004 independently passed eleven original cases: ten real numerical solves and
one original multi-instance creation case, no skip. Full native build and two-rank
Fortran MPI probe passed in the same transaction; release/postrelease and own0 verified.
Proof SHA256: 1e9fccfba0dfe83df755ddbe758c7edbdd2757dbcc44b0f2a6ab096834540318.
That historical native proof is not formal Conan, a published provider, FEniCS completion, or platform CI PASS.

## Current official formal evidence

Fresh r322 executed the unchanged official finish local CI and native Conan build/package/test.
The original eleven cases, four MPI consumer checks and one signed HarmonyOS-specific check
all passed without skipping. The full original Git root whitelist genuinely executed with
the signed real Git tool and the exact 116194-entry staged index; r314's missing-Git empty
loop remains an invalid whole-gate result and is not reused.
Independent mumps-formal-observed-oct10-r329.json validates the same-run numeric solutions,
complete WAL/receipts, sole launch and own0/release/postrelease.
This proves formal local validation only: platform CI, Review, submission, publication
and FEniCS closure remain separate and are not inferred.
