# tcpstat

## Description

tcpstat is an active TCP connections monitoring tool with a curses-based TUI interface. It displays real-time TCP connection statistics by reading from `/proc/net/tcp`, showing information grouped by destination IP, port, connection state, or interface.

## Available Versions

| Version | Status | Build System | Notes |
|---------|--------|--------------|-------|
| 0.1 | published | makefile | Requires ncurses |

## Dependencies

- ncurses (static library)

## Build Notes

- Source uses a hand-written Makefile (not autotools)
- HarmonyOS platform adaptations: SYS detection, musl header fixes, ncurses paths
- No test suite available
