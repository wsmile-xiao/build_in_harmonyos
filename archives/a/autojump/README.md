# autojump

> A faster way to navigate your filesystem

## Description

autojump is a command-line utility that allows users to quickly navigate to frequently used directories by using a weighted history of directory visits. Instead of typing long paths, users can simply type `j <partial_directory_name>` to jump to directories they've visited before.

## Key Facts

- **Type**: Pure Python/bash script project (no C compilation)
- **Version**: 22.5.3
- **License**: GPL-3.0-or-later
- **Source**: https://github.com/wting/autojump

## Platform Notes

- No ELF binaries - does not require signing
- Shell integration required: source `autojump.sh` in shell RC file
- /etc/profile.d is read-only on HarmonyOS, so autojump.sh is placed under prefix/etc/profile.d/
- Hardcoded `/usr/local` paths in autojump.sh must be replaced with DEFAULT_PREFIX

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 22.5.3 | built | 2026-06-01 |
