# incron

inotify cron system - handles filesystem events instead of time periods

## Description

incron is a daemon which watches filesystem events and executes commands defined in user tables. It works similarly to cron, but instead of time-based scheduling, it uses inotify to detect filesystem changes.

## Components

- **incrond**: The daemon that monitors filesystem events
- **incrontab**: The table manipulator for managing watch rules

## Usage

```bash
# View current incrontab
incrontab -l

# Edit incrontab
incrontab -e

# Remove incrontab
incrontab -r
```

## Configuration

User table syntax:
```
<path> <event> <command>
```

Example:
```bash
/var/mail IN_CLOSE_WRITE abc $@/$#
/tmp IN_ALL_EVENTS efg $@/$# $&
```

## Documentation

- [GitHub Repository](https://github.com/ar-/incron)
- [README.md](https://github.com/ar-/incron/blob/master/README.md)

## Compiled Version

- Version: 0.5.12
- Build Date: 2026-05-26
- Status: built

## Dependencies

- argp-standalone (for argp.h header)

## Notes

This software requires Linux kernel 2.6.13+ with inotify support.