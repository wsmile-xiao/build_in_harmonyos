# rdiff-backup

rdiff-backup is a Python backup and restore tool using reverse incremental
backups and librsync deltas.

## Versions

- 2.2.6: adapted for HarmonyOS PC.

## Notes

- The package builds the upstream CPython extensions `rdiff_backup.C` and
  `rdiff_backup._librsync`.
- Runtime depends on `librsync/2.3.4` and `pyyaml/6.0.2`.
