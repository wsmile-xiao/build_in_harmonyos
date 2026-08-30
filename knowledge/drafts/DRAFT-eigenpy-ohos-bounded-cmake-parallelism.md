# DRAFT: eigenpy OHOS bounded CMake parallelism

> Status: Draft | Updated: 2026-08-29
> Source event: `eigenpy/3.13.0` official CI #34250 `conan create` timeout

## Summary

`eigenpy` builds many Eigen/Boost.Python translation units. On OHOS CI, a
serial CMake build can pass configure and link fixes but still exceed the
3600s `conan create` budget before packaging and `test_package` run. Keep the
installed library set unchanged, but bound the CMake build parallelism so the
template-heavy compile fits CI.

## Symptoms

- Previous link errors are resolved and `libeigenpy.so` starts compiling.
- The CI log ends with `conan create TIMED OUT after 3600s`.
- `L0_RESULT=pass`, `L1_RESULT=fail: conan create timed out`.
- The failure can be misclassified as source download timeout because the full
  log contains earlier download URLs.

## Adaptation Pattern

Use the Conan `tools.build:jobs` conf, default OHOS builds to two jobs, and cap
OHOS jobs at two to avoid memory pressure. Prefer Ninja when it is present in
the worker PATH; otherwise keep the default CMake generator and still pass
`--parallel <jobs>`:

```python
def _cmake_generator_arg(self):
    if self.settings.os == "OHOS" and shutil.which("ninja"):
        return '-G "Ninja"'
    return ""

def _build_jobs(self):
    default_jobs = 2 if self.settings.os == "OHOS" else (os.cpu_count() or 1)
    configured = self.conf.get("tools.build:jobs", default=default_jobs, check_type=int)
    if self.settings.os == "OHOS":
        return max(1, min(configured, 2))
    return max(1, configured)
```

Run the build with `cmake --build <dir> --parallel <jobs>`.

## Validation

- Device shadow CI should still pass all package checks.
- Official CI should progress past `conan-build-test` without the 3600s timeout.
- `test_package` must remain non-stub and continue linking `libeigenpy`.

## Do Not

- Do not remove eigenpy modules or headers only to reduce compile time.
- Do not use unbounded `os.cpu_count()` parallelism on constrained OHOS workers.
