# safekeep

Conan recipe for SafeKeep, a Python-based backup manager that orchestrates
incremental backups across hosts using `rdiff-backup`.

## Package

- Version: 1.5.1
- Upstream: https://github.com/dimipaun/safekeep
- Homepage: http://safekeep.sourceforge.net/
- License: GPL-2.0-or-later

The package installs the main `safekeep` command under `bin/` and keeps sample
configuration, cron, documentation source, and sample backup definitions under
`share/safekeep`.

## Runtime Notes

SafeKeep is a Unix-oriented tool. Runtime use requires Python 3 and external
system tools such as `rdiff-backup` and OpenSSH. Snapshot and database backup
features may require additional platform utilities.
