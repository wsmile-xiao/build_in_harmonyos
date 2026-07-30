# lua-proctitle

lua-proctitle is a Lua C module for changing the current process name.

## OpenHarmony Adaptation

The upstream 0.1 implementation uses glibc's `__progname`, which is not
available on OpenHarmony. The OpenHarmony build uses `prctl(PR_SET_NAME)` to
set the process name instead. Linux limits this name to 15 bytes plus the
terminating null byte.

## Dependencies

- `lua/5.4.8`

## References

- Homepage: https://github.com/hoelzro/lua-proctitle
- License: MIT
