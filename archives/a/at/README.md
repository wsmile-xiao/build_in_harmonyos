# at

**at** is a command scheduler that allows users to schedule commands to be executed at a specified time. It includes:

- `at` — schedule one-time commands
- `atq` — list scheduled jobs
- `atrm` — remove scheduled jobs
- `batch` — schedule commands for execution when system load is low
- `atd` — the background daemon that executes scheduled jobs
- `atrun` — compatibility wrapper for atd

## Versions

| Version | Status | Date |
|---------|--------|------|
| 3.2.5 | built | 2026-06-29 |

## Build System

Autotools (autoconf 2.69)

## Patches

Three platform patches are applied for HarmonyOS compatibility:
1. config.guess — HarmonyOS system identification
2. config.sub — linux-ohos triplet support
3. configure — cross-compile fix (E064) + HMDFS mktemp workaround
