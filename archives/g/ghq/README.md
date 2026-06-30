# ghq

ghq is a Git repository management tool written in Go. It provides a way to organize and manage local Git repository clones with a unified directory structure, and makes it easy to clone, list, and find repositories.

## Features
- Manage Git repositories in a unified directory structure
- Clone repositories from GitHub, GitLab, and other Git hosting services
- List and search local repositories
- Migrate repositories between remote hosts

## Version
- 1.9.4 (compiled for OpenHarmony aarch64)

## Dependencies
- Go 1.26+ (for building)

## Install
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- ghq 1.9.4
```

## Verify
```bash
ghq --version
# ghq version 1.9.4 (rev:HEAD)
```
