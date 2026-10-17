# zimfw

zimfw (Zim Framework) is a Zsh plugin manager that helps you install and manage Zsh plugins with speed and simplicity.

## Requirements

- Zsh 5.2 or newer

## Installation

After installing via Conan, source the script in your `.zshrc`:

```zsh
# Set ZIM_HOME
export ZIM_HOME="$HOME/usr/local/share"

# Source zimfw
source "$ZIM_HOME/zimfw.zsh"
```

When installed under the OpenHarmony user prefix, use:

```zsh
export ZIM_HOME="$HOME/usr/local/share"
source "$ZIM_HOME/zimfw.zsh"
```

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 1.20.0 | built | 2026-07-17 | Pure Zsh script; packaged via Conan |

## Upstream

- Homepage: https://zimfw.sh
- License: MIT
