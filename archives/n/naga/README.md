# naga

Terminal implementation of the Snake game; made with C and ncurses.

## Upstream

- GitHub: https://github.com/anayjoshi/naga
- License: BSD-3-Clause

## Version

- 1.0 (upstream has no tags; source is master HEAD commit 924af37, pinned)

## Build System

- makefile-custom (7 translation units compiled directly with Conan clang;
  upstream Makefile hardcodes CC=gcc and lacks DESTDIR support)

## Dependencies

- ncurses/6.4 (Conan dependency, headers + static libs only)

## Test Report

Upstream ships no test suite (see 1.0/test_package/MANIFEST.yml audit).
test_package exercises the game logic via libnaga.a (12 assertions).
