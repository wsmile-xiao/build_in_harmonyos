# gotop

A terminal based graphical activity monitor, inspired by gtop and vtop.

## Description

gotop is a terminal-based dashboard that displays system metrics including CPU, memory, disk, network, and process information using a TUI (Terminal User Interface) based on termui.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 4.2.0   | built  | 2026-05-26 |

## Build Notes

- Pure Go project (CGO_ENABLED=0)
- Build command: `go build -ldflags="-X main.Version=4.2.0 -X main.BuildDate=YYYY-MM-DD" -o gotop ./cmd/gotop`
- Requires Go 1.16+ (tested with Go 1.24.4)
- Important: Go linker requires hmfs filesystem for TMPDIR (HMDFS doesn't support mmap write operations)
