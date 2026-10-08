# wcd/6.0.6 for HarmonyOS PC

WCD is a command-line directory changer written in C. A child process cannot
change its calling shell's directory, so users must source the packaged
`share/wcd/wcd.sh` function from their interactive shell. The package keeps
the binary, manual, and this function together.

This adaptation builds the official 6.0.6 source on HarmonyOS PC AArch64 with
Clang, with optional gettext/NLS and curses UI disabled. The upstream release
contains data fixtures but no automated test target. The Conan consumer test
scans an isolated tree, selects a directory, checks the generated `wcd.go`,
and verifies that sourcing the shell function changes the caller's directory.

On a restricted HarmonyOS PC SSH account, `HOME` may not be writable. Set
`WCDHOME` to an application-owned directory before using WCD. `WCDHOME`
controls state files; it does not control the default scan root in this
release. Use `wcd -S <directory>` or `WCDSCAN` for a bounded scan.
