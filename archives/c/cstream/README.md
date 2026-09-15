# cstream

General-purpose stream-handling tool like UNIX dd, usually used in commandline-constructed pipes.

## Overview
cstream filters data streams with precise bandwidth limiting, throughput reporting, FIFO support,
built-in data generation/sink, and TCP/audio options. Upstream by Martin Cracauer, version 4.0.0.

## Versions
- 4.0.0 (current)

## OHOS adaptation
- Autotools build with explicit `--build/--host=aarch64-unknown-linux-gnu` to bypass old config.guess.
- `make check` is a no-op upstream (TESTS commented out); real suite `tests/test1.sh small` runs in build().
- No external dependencies; single binary `bin/cstream`.
