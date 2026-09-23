# nvm

Node Version Manager — Simple bash script to manage multiple active node.js versions.

## Description

nvm is a POSIX-compliant bash function that allows users to manage multiple active Node.js versions. It is sourced (not executed) to provide the `nvm` command.

## Homepage

https://github.com/nvm-sh/nvm

## Dependencies

nvm requires:
- bash (preinstalled)
- curl or wget (for downloading Node.js versions)
- git (optional, for building Node.js from source)

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- nvm 0.40.6
```

## Usage

After installation, source nvm.sh in your shell:

```bash
export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
```

Then you can manage Node.js versions:

```bash
# Install a Node.js version
nvm install 18.0.0

# Use a specific version
nvm use 18.0.0

# Set default version
nvm alias default 18.0.0

# List installed versions
nvm ls
```

## Available Versions

| Version | Status | Build Date |
|---------|--------|------------|
| 0.40.6 | built | 2026-09-14 |

## Notes

- This is a pure shell script project, no compilation required
- nvm.sh must be sourced (not executed) to use the nvm command
- The urchin test framework is used for testing (297 registered tests)
- No patches needed — nvm.sh has built-in platform detection for aarch64
