# Bash Argsparse

Bash Argsparse is a high-level command-line argument parsing library for GNU
Bash, inspired by Python's `argparse` module.

## Features

- Declares long and short command-line options
- Generates help and usage output
- Supports required values, defaults, aliases and mutually exclusive options
- Validates common value types
- Provides Bash completion helpers

## HarmonyOS adaptation

The package contains Bash scripts and does not compile native code. HarmonyOS
PC does not provide the external GNU `getopt` command used by upstream, so the
adaptation adds a Bash-native fallback which normalizes long options, short
option clusters, option values, `--`, and positional arguments.

The scripts are installed below `share/bash-argsparse`. Conan exports that
location through the `BASH_ARGSPARSE_ROOT` runtime environment variable.

## Dependencies

- `bash/5.3`

## References

- Upstream repository: https://github.com/Anvil/bash-argsparse
- Debian source package: https://packages.debian.org/stable/bash-argsparse
