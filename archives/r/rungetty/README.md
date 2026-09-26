# rungetty

rungetty is a small console getty: instead of always running `/bin/login`, it
takes over a tty line (sets up the controlling terminal, flushes the line
discipline and installs the standard descriptors) and executes an arbitrary
program on it. It is the classic "getty that runs anything" used from `/etc/inittab`,
derived from mingetty.

Upstream: `http://ibiblio.org/pub/Linux/system/serial/getty/` (single C file plus
a bare Makefile, GPL-2.0-or-later, last release 1.2).

The `1.2` recipe declares no Conan dependencies (libc only) and installs
`bin/rungetty` plus the `man8` page. Because rungetty is a console program, the
OpenHarmony behaviour of the TTY interfaces it relies on was measured with a
standalone probe on the device; see `1.2/notes.md` 附录 A/B for the raw
readings (`TIOCSCTTY` works for a session leader, `TCFLSH` returns `EACCES`,
`vhangup(2)` is refused by the platform syscall filter) and for the adaptation
boundary those readings define.
