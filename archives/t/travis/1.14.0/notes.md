# Notes — travis 1.14.0

## Build Summary

`travis` is a Ruby gem CLI for Travis CI. The package is distributed on
RubyGems and requires Ruby `>= 3.2.0`.

This adaptation treats it as a script-based command-line tool:

1. download `travis-1.14.0.gem` from RubyGems
2. unpack the upstream `.gem` payload directly into the Conan package tree
3. expose a wrapper in `bin/travis`
4. keep `version` available offline even when the build/test worker has no Ruby

## Why this packaging strategy

- there is no native `configure` / `make` / `cmake` build flow
- the upstream CI worker for this repository does not guarantee a Ruby runtime
- packaging must therefore avoid `gem install` in `package()`

## Runtime Expectations

- `travis version` works offline without Ruby so CI can do a stable smoke test
- other subcommands still require a Ruby runtime in the consumer environment
- the package ships the upstream gem payload, but does not try to resolve and
  install the full RubyGems dependency graph during Conan packaging

## CI Risk Control

The upstream project contains 284 RSpec examples. They are conditionally
executed by `run_upstream_tests.sh` when a worker provides Ruby, Bundler, the
installed dependency bundle, and a complete upstream source tree. The default
offline Conan worker cannot run them because:

- some tests depend on the Ruby development toolchain and Bundler workflow
- the CLI itself can touch networked Travis endpoints in many subcommands
- the published `.gem` does not contain the upstream `spec/` tree
- `conan-build-test` cannot fetch the missing bundle or contact test endpoints

Therefore `test_package` verifies:

- the packaged `travis` executable exists
- the packaged wrapper is executable
- the wrapper contains an offline `version` fast-path
- `version`, `--version`, and `-v` return the exact expected version
- `travis version` works with an empty tool `PATH`, proving it does not invoke Ruby

## Test Results

| Test set | Available | Executed | Passed | Pass rate | Result |
|---|---:|---:|---:|---:|---|
| Upstream RSpec examples | 284 | 0 | 0 | 0% | Skipped by default; conditionally executed when all offline prerequisites exist |
| HarmonyOS/offline smoke assertions | 7 | 7 | 7 | 100% | Passed |

The adapted test count is **7**, not 291. The 284 upstream examples are
reported separately because they are not executed in the current CI run.
