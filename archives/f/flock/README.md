# flock

**flock** — manage file locks from shell scripts

flock is a utility from [util-linux](https://github.com/util-linux/util-linux) that provides the ability to manage file locks from shell scripts. It allows exclusive, shared, and non-blocking locks on files or directories, commonly used to prevent concurrent access in cron jobs, init scripts, and other automation tasks.

## Available Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 2.40.2 | published | 2026-06-09 | Compiled from util-linux v2.40.2, selective build |

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- flock 2.40.2
```

## Usage

```bash
# Exclusive lock (wait until available)
flock /tmp/myapp.lock my_command

# Non-blocking lock (fail immediately if locked)
flock -n /tmp/myapp.lock my_command

# Shared lock (allow concurrent readers)
flock -s /tmp/myapp.lock my_reader_command

# Lock with timeout
flock -w 30 /tmp/myapp.lock my_command

# Lock using file descriptor (advanced)
exec 9>/tmp/myapp.lock
flock 9
# ... commands run while lock is held ...
exec 9>&-
```

## Notes

- flock is compiled from the util-linux project source, but only the flock binary is packaged
- Other util-linux commands (mount, umount, etc.) are NOT included