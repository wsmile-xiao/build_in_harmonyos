# zsh-autopair

zsh-autopair is a Zsh plugin that auto-closes, deletes, and skips over matching delimiters such as quotes, brackets, braces, and paired spaces.

## Requirements

- Zsh 5.0.2 or newer

## Installation

Source the installed plugin file in `.zshrc`:

```zsh
source /usr/local/share/zsh-autopair/autopair.zsh
autopair-init
```

When installed under the OpenHarmony user prefix, use:

```zsh
source $HOME/usr/local/share/zsh-autopair/autopair.zsh
autopair-init
```

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 1.0 | built | 2026-07-14 | Pure Zsh script plugin; packaged via Conan |

## Upstream

- Homepage: https://github.com/hlissner/zsh-autopair
- License: MIT
