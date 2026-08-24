# bash-argsparse 1.8.22.ga05fe6d adaptation notes

## Scope

This adaptation packages the two upstream Bash libraries and the tutorial
scripts. There is no native compilation step.

## Source

- Upstream: https://github.com/Anvil/bash-argsparse
- Debian snapshot version: `1.8.22.ga05fe6d`
- Archive size: 52,464 bytes
- SHA256: `1fbd1876a8b3b0d3da67e9aa46b01d87c81f1b397cac28952dbac31006dbd651`

## Existing knowledge used

1. `knowledge/ARCHIVE-SPEC.md` defines the v3 Conan archive layout and required
   metadata/test files.
2. `archives/b/bash-completion/2.17.0` provides the repository pattern for a
   pure Bash package with no native artifacts.
3. `archives/a/acr/2.2.6` records that the HarmonyOS PC base image lacks the
   external `getopt` utility.

## Compatibility change

Upstream exits while being sourced when `getopt` is missing. The portability
patch keeps the original GNU `getopt` path when the command exists and adds a
Bash-native fallback otherwise. The fallback supports:

- exact long options and `--option=value`
- individual and clustered short options
- values attached to short options or supplied as the next argument
- the `--` option terminator
- GNU-style permutation of positional arguments after parsed options
- clear errors for unknown options and missing values

After normalization, upstream's existing validation, aliases, exclusions,
required options, types, hooks and result arrays remain unchanged.

The upstream test suite also assumes `getent` and older Bash internal state.
The second portability patch filters Bash 5.3's transient `BASH_TRAPSIG`
variable and skips only the NSS-backed positive username/group cases when
`getent` is unavailable. Self-contained parser and type checks still run.

## Validation plan

- Run the complete upstream `unittest` script during `conan create`.
- Run the consumer test with `ARGSPARSE_FORCE_INTERNAL_GETOPT=1` so the
  HarmonyOS fallback is exercised even on hosts which provide GNU `getopt`.
- Verify a short-option cluster, a long option with value and a positional
  parameter through the packaged script.

## Local results

- Patch application: passed
- Consumer fallback smoke test with Bash 5.3.15: passed
- Complete upstream `unittest` with forced internal fallback: passed
  (`5` environment-dependent cases disabled on macOS)
- Conan recipe inspection, Python compilation and YAML parsing: passed

## Current verification boundary

The recipe and Python/YAML files are statically checked locally. The packaged
`bash/5.3` binary and final `conan create` must run in the HarmonyOS PC pipeline.
