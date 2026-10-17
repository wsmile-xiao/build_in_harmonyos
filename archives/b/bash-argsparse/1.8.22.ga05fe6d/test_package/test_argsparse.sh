#!/usr/bin/env bash
set -euo pipefail

library=${1:?usage: test_argsparse.sh PATH_TO_ARGSPARSE_SH}

# Exercise the HarmonyOS fallback even when the test host has GNU getopt.
export ARGSPARSE_FORCE_INTERNAL_GETOPT=1
source "$library"

[[ $ARGSPARSE_VERSION == 1.8 ]]

argsparse_use_option =verbose "Increase verbosity"
argsparse_use_option =output: "Output file"
argsparse_describe_parameters input

# Options intentionally follow a positional argument to verify permutation.
argsparse_parse_options payload -vv --output=result.txt

[[ ${program_options[verbose]} -eq 2 ]]
[[ ${program_options[output]} == result.txt ]]
[[ ${#program_params[@]} -eq 1 ]]
[[ ${program_params[0]} == payload ]]

printf 'bash-argsparse smoke ok\n'
