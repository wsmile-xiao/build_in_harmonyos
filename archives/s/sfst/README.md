# sfst

SFST (Stuttgart Finite State Transducer) is a toolkit for computational
morphology: an fst compiler plus runtime analysers/generators
(`fst-compiler`, `fst-infl`, `fst-mor`, `fst-print`, ...).

## OHOS adaptation

- Builds the C++ library (`libsfst`) and CLI tools with CMake/C++17.
- Python bindings are guarded off: the 1.7.0 release tarball archives an
  empty `pybind11/` submodule directory, so the top-level descent into
  `pybind11/`/`python/` is made conditional in `source()` via
  `replace_in_file` (no patch file).
- `flex`/`bison` are optional upstream: `fst-*` tools build only when both
  are found natively, otherwise the supported artifact is library-only;
  `readline` provides interactive line editing for the compiler tools.
- Upstream registers no CTest tests for the C++ artifacts; the only test
  file (`python/tests/test.py`) targets the pybind11 extension and is out
  of scope. Consumer coverage links `libsfst` (`Alphabet` API) and runs
  `fst-infl -v`.

## Dependencies

- `readline/8.3` (runtime library; only recipe dependency)
- `flex`/`bison`: no `tool_requires` (native PATH probe only; absent means
  upstream-supported library-only build)

## References

- https://github.com/santhoshtr/sfst
- VERSION: 1.7.0
