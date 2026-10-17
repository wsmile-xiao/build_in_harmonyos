# ndenv

Node.js version manager based on rbenv (shell scripts).

## Description

ndenv manages multiple Node.js/io.js versions following the rbenv model:
a `bin/ndenv` dispatcher plus `libexec/ndenv-*` subcommand scripts and
shell completions. Unlike nvm, it switches versions automatically via a
per-project `.node-version` file. Almost all code comes from rbenv.

## Homepage

https://github.com/riywo/ndenv

## Dependencies

ndenv itself has no build dependencies (pure shell scripts). Its
`install` subcommand works together with the `node-build` plugin at
runtime when actually installing Node.js versions.

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- ndenv 0.4.0
```

## Usage

After installation, initialize ndenv in your shell:

```bash
eval "$(ndenv init -)"
```

Then you can manage Node.js versions:

```bash
# List installed versions
ndenv versions

# Show current version
ndenv version

# List available commands
ndenv commands
```

## Available Versions

| Version | Status | Build Date |
|---------|--------|------------|
| 0.4.0 | built | 2026-09-12 |

## Notes

- This is a pure shell script project, no compilation required
- Upstream ships no test suite; test_package provides a 6-assertion smoke test
- Upstream is deprecated in favor of nodenv, but 0.4.0 remains the requested version
