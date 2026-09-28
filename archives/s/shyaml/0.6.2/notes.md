# shyaml 0.6.2 adaptation notes

## Packaging

`shyaml` is a pure-Python single-module CLI. The Conan recipe copies the module into versioned
`site-packages` and creates a relocatable `bin/shyaml` launcher. PyYAML 6.0.2 is a runtime dependency.

The pinned GitHub codeload archive has no `.git` directory. The upstream `setup.py` sees its
`%%version%%` template and invokes `autogen.sh`, whose version discovery requires
`git describe --tags`; Conan therefore stages the pure module directly and substitutes the pinned
release version in the module.

## Upstream tests

The official `bin/test` entry point uses Bash arrays and docshtest shell examples. OHOS workers do
not provide `bash`, so `build()` runs the two Python doctest suites directly: 33/33 in `shyaml.py`
and 4/4 in `README.rst`. The 64 README shell examples are recorded as not run because the upstream
entry point requires Bash. This avoids the worker's `FileNotFoundError: bash` while retaining 37
real upstream checks. On 2026-09-27, HarmonyOS `conan create` exited 0 and the installed
`test_package` completed its five CLI assertions.

## Consumer tests

The HarmonyOS test package checks the installed launcher, version, nested mapping lookup, sequence
indexing, and YAML scalar type. The updated `conan create` verifies these after packaging.
