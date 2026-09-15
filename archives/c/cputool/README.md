# cputool

CPU usage and system load management tool for Linux/HarmonyOS.

CPUTool limits the CPU usage of a process or process group to a given limit
and suspends process execution when the system load exceeds a threshold. It
works by sending SIGSTOP and SIGCONT signals, and can manage already-running
processes (by PID) or launch and supervise a new command.

- **License**: GPL-3.0-or-later
- **Homepage**: https://gitlab.linux.community/cputool/cputool/
- **Version**: 1.1.0

## OpenHarmony Build Notes

- Built with the OHOS clang toolchain via Meson (`-Ddocs=disabled`,
  `-Ddefault_library=static`); man pages are skipped because `rst2man`
  (python3-docutils) is unavailable on OHOS, and the lookup is patched to
  be non-fatal when docs are disabled.
- Upstream is pure POSIX C (dirent/getopt/signal/sys-wait), no Linux-only
  headers; runtime process stats come from `/proc`, whose availability on
  OHOS may limit live supervision scenarios (build and CLI self-checks
  are unaffected).
- Upstream ships no test suite; functional coverage lives in
  `test_package/test_cputool.sh` (5 content-level checks over bin/cputool).
- No external dependencies (libc only).

## References

- Upstream: https://gitlab.linux.community/cputool/cputool/
- Debian packaging: https://salsa.debian.org/salvage-team/cputool
