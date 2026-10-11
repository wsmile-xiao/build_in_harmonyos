# spew

spew is an I/O performance measurement and load generation tool for regular files, character devices, and block devices. It can write and verify deterministic data patterns through the `spew`, `gorge`, and `regorge` command modes.

## OHOS adaptation

- Builds the official upstream 1.0.8 tag with Autotools.
- Uses published `popt/1.16` and static `ncurses/6.6` dependencies.
- Packages the three upstream command modes without changing their behavior.
- Runs the complete upstream `make check` target and ten installed-package assertions, including an OHOS private-`TMPDIR` data-integrity cycle and deliberate corruption detection.
- Reports the real OHOS triplet (no fake GNU `--build/--host` triplets) and normalizes the HMDFS `umask 077` config.status issue.

## References

- https://github.com/apatters/spew
