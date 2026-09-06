# nsuds

nsuds — The Ncurses Sudoku System. A text-graphical sudoku game with
pencil-marking support, written in C. The only library dependency is ncurses.

## Upstream
- SourceForge: https://sourceforge.net/projects/nsuds/
- GitHub mirror: https://github.com/jubalh/nsuds (official mirror, master == 0.7B)
- License: GPL-2.0

## Version
- Upstream 0.7B (AC_INIT([nsuds], [0.7B]); tag nsuds-0.7B / commit cd0c9b5a
  upstream; archive snapshot jubalh/nsuds @ 003eecf9).
- Conan recipe version is lowercased to `0.7b` (Conan 2 requires lowercase
  recipe references); the binary still reports "nsuds version 0.7B".

## Build System
- Autotools (configure.ac + Makefile.am; git archive ships no generated
  configure → autoreconf bootstrap in build(), automake via conan tool_requires)

## Dependencies
- ncurses/6.6 (Conan dependency, static wide-char build — R26: never install a
  shared ncurses that would shadow the OHOS system lib)

## Test Report
See [0.7b/reports/test-report.md](0.7b/reports/test-report.md) for detailed
test results. Upstream ships no test suite (`make check` is a no-op); the
packaged binary's non-interactive CLI (--version/-v/--help/-h) is exercised
by test_package/test.sh.
