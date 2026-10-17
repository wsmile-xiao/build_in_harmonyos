# plenv

plenv is a simple Perl version manager in the rbenv style, implemented in pure Bash.
It manages Perl versions under `~/.plenv/versions/` and exposes them through shims.

This archive packages plenv 2.3.1 as a command-line tool for OpenHarmony PC
arm64/OHOS. The package installs the upstream `plenv` executable, the 28
`libexec/plenv-*` subcommands, shell completions, and `plenv.d` hooks without
any native compilation.
