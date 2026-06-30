# podman-tui

Podman terminal UI — a TUI (terminal user interface) for managing Podman containers, pods, and images.

## Description

podman-tui provides an interactive terminal interface for managing Podman containers, pods, volumes, and images. It uses the tview library for rendering the TUI.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 1.9.0 | built | 2026-06-04 |

## Build Notes

- Go language project with vendor directory
- CGO_ENABLED=0 (static binary, no C dependencies)
- Build tags: exclude_graphdriver_btrfs, containers_image_openpgp, remote
- GOPROXY=https://goproxy.cn,direct recommended for Chinese network