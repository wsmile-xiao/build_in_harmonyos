# ccmeta

Let Claude Code drive its own meta commands (/clear, /compact, /model, /loop) via tmux. Ships as Agent Skill - safe tier + opt-in dangerous tier for autonomous loops and remote ops.

- Homepage: https://github.com/Alfredvc/ccmeta
- Version: 1.0.0 (commit 26e7b1d on main, no tagged release - pinned to latest stable commit)
- License: MIT
- Build: shell-only, no compiled binary - shared/ccmeta-core.sh and skill definitions are installed to share/ccmeta

## OHOS Adaptation

No code changes required for HarmonyOS PC aarch64. The framework is POSIX shell; `sh -n` syntax validation is used as the upstream smoke check. A lightweight `bin/ccmeta` wrapper is installed for Conan package validation and to expose the installation path.

## Test

Consumer test checks that `share/ccmeta/shared/ccmeta-core.sh` and both skill directories exist and that `bin/ccmeta` executes successfully.
