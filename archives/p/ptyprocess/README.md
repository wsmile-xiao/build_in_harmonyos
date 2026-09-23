# ptyprocess

`ptyprocess` runs subprocesses in pseudo terminals on POSIX systems.

- Upstream: https://github.com/pexpect/ptyprocess
- Version adapted: 0.7.0
- Package type: pure-Python library (`python-require`)
- Runtime import path: `lib/pythonX.Y/site-packages/ptyprocess`

The version recipe builds the upstream wheel, runs the complete upstream test suite,
and includes a Conan consumer smoke test that exercises real PTY child-process I/O.
