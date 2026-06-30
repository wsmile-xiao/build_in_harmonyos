# nodenv

Node.js version manager similar to rbenv.

## Description

nodenv is a lightweight Node.js version manager that allows you to easily switch between different Node.js versions. It follows the rbenv model, providing a simple and unobtrusive way to manage Node.js installations.

## Homepage

https://github.com/nodenv/nodenv

## Dependencies

nodenv requires `node-build` to compile and install Node.js versions:
- node-build (available in cmd-pkgs)

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- nodenv 1.6.2
```

## Usage

After installation, initialize nodenv in your shell:

```bash
eval "$(nodenv init -)"
```

Then you can manage Node.js versions:

```bash
# Install a Node.js version (requires node-build)
nodenv install 18.0.0

# Set global version
nodenv global 18.0.0

# Set local version (for current directory)
nodenv local 18.0.0

# List installed versions
nodenv versions
```

## Available Versions

| Version | Status | Build Date |
|---------|--------|------------|
| 1.6.2 | built | 2026-06-05 |

## Notes

- This is a pure shell script project, no compilation required
- The path prefix needs to be modified in libexec/nodenv
- Requires node-build plugin for actual Node.js version installation