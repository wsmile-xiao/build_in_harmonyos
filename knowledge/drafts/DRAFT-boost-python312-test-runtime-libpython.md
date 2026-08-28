# DRAFT: Boost.Python test_package runtime libpython on HarmonyOS PC

> Status: Draft | Updated: 2026-08-26
> Source event: `boost/1.90.0.2.1` shadow CI runtime validation
> Task hall: `4415`
> PR: https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/6712

## Summary

A Boost.Python consumer test can pass configure and link, then fail only when
the executable starts on the OHOS device. The missing piece is often not a Conan
package library, but the external CPython shared library used to build
`libboost_python312.so`.

Keep Conan's `VirtualRunEnv` for packaged dependencies, then prepend the selected
CPython library directory for the one runtime invocation.

## Symptoms

Typical runtime failures include:

- `libpython3.12.so.1.0: cannot open shared object file`
- `undefined symbol: Py_Initialize`
- `undefined symbol: PyType_Type`
- Boost.Python consumer builds successfully but fails during shadow CI execution.

The first `boost/1.90.0.2.1` shadow iteration built `libboost_python312.so`, but
test execution failed until the CPython libdir was added to the OHOS test runtime
environment.

## Root Cause

Conan `VirtualRunEnv` knows about Conan package dependencies. It does not
necessarily know where the target device's CPython runtime is installed. On the
current OHOS runner, CPython 3.12 lives under `~/usr/local`, outside the Boost
Conan package. The dynamic loader therefore needs an additional search path for
the Python shared library.

This is a runtime environment issue, not proof that Boost.Python failed to build.

## Adaptation Pattern

In `test_package`, keep `VirtualRunEnv`, sign the executable for OHOS, discover
the same CPython runtime used by CMake, and run with the CPython libdir prepended:

```python
VirtualRunEnv(self).generate()

if self.settings.os == "OHOS":
    self._sign_executable(executable)
    python_libdir = os.path.dirname(self._discover_python()["library"])
    command = 'LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}" "{}"'.format(
        python_libdir, executable
    )
    self.run(command, env="conanrun", cwd=self.build_folder)
```

The prepend keeps Conan's own runtime environment intact and adds only the
external Python runtime location that Boost.Python needs.

## Validation

The consumer should do real Boost.Python work at runtime, not just link an empty
program. The `boost/1.90.0.2.1` test initializes CPython and exercises:

- `boost::python::dict`
- `boost::python::extract<int>()`

The passing shadow CI result was:

```text
L0=pass, L1=pass, L2=skip(no bin/ dir), L4=pass, L5=pass; Build Summary Total=1 Success=1 Failed=0
```

## Do Not

- Do not ignore the runtime command's exit code.
- Do not replace the runtime test with compile-only validation for a runnable
  OHOS package.
- Do not copy `libpython` into the Boost package to hide the missing runtime
  path; the Python runtime should remain owned by the Python installation.
