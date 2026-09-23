# E2176-draft-A7F3 - Task-owned Python dependency and source-closure validation

## Problem pattern

Pure-Python packages can appear source-complete while a minimal Conan worker lacks their third-party Python runtime. ConfigSpace imports SciPy-backed hyperparameter classes and `more_itertools` helpers during package initialization, so its empty-configuration smoke can fail before exercising the package when those modules are absent. A host package build also says nothing about whether the target has Python or Conan.

## Reusable resolution

1. Bind the recipe to an official, hash-verified source archive. If the release sdist omits files required by the upstream test inventory, use the official tagged source closure and record both URL and SHA-256.
2. Install test-only dependencies in a task-owned directory and pin incompatible test tooling, rather than changing the system interpreter.
3. If the CI worker cannot provide those dependencies and no Conan package exists, verify the package marker and emit an explicit dependency-missing `SKIP` before importing the library. Do not create numerical-library fakes or report an API pass from a reduced environment.
4. Run the complete dependency-backed upstream test inventory and retain its exact denominator and terminal result.
5. Use a task-isolated Conan home when OHOS is absent from the host settings. Before W3, probe the target for actual Python/Conan capability; if absent, bootstrap only a frozen task-owned runtime closure with complete hashes.

## Evidence and limits

ConfigSpace 1.2.2 Buildbot #37072 reached package creation but failed because the worker's Python had no `scipy`; #37106 then showed the same worker also had no `numpy`. The corrected smoke now verifies the package marker and emits a dependency-missing `SKIP` instead of faking numerical modules. With the task-owned OHOS runtime closure, the target passed 330/330 upstream tests and the consumer smoke. The reduced CI smoke does not establish API or numerical dependency correctness and cannot replace the target evidence.

## Applicability

This pattern applies to pure-Python packages with eager external imports, omitted test data, or restricted target runtimes. It does not replace dependency-backed upstream testing, target validation, or permit changing shared tool directories.
