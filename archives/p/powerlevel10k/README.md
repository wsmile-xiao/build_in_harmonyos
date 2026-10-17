# powerlevel10k

Powerlevel10k is a Zsh theme with emphasis on speed, flexibility and
out-of-the-box experience.

## Requirements

- Zsh 5.1 or newer (upstream README)

## Installation

Add the theme to your `.zshrc`:

```zsh
source <pkg>/share/powerlevel10k/powerlevel10k.zsh-theme
```

(e.g. `source $HOME/usr/local/share/powerlevel10k/powerlevel10k.zsh-theme`
when installed under the OpenHarmony user prefix), then restart zsh and run
`p10k configure` to generate the user configuration.

Note: this package ships the pure zsh scripts only — the gitstatusd daemon
(C++ vcs acceleration backend) is intentionally not packaged.  The theme
falls back to zsh's native `vcs_info` for git segments (upstream-supported
degradation; see 1.20.0/notes.md for the full decision record).

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 1.20.0 | built | 2026-09-03 | Pure zsh scripts; share-only package; gitstatusd not shipped (vcs_info fallback) |

## Upstream

- Homepage: https://github.com/romkatv/powerlevel10k
- License: MIT
