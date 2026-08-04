pick is an interactive fuzzy selection tool for terminal pipelines.

## Features

- Reads candidate lines from standard input.
- Provides an ncurses-based interactive filter.
- Prints the selected line to standard output.

## OHOS adaptation

- Upstream uses Autotools.
- The recipe uses `DEFAULT_PREFIX` and bundled ncurses headers; when a usable ncurses Conan recipe is unavailable, the small terminfo API subset used by pick is built from `res/src` source during `build()`.
- `config.guess` and `config.sub` are patched during `build()` for OHOS recognition.
- The upstream Automake tests are invoked through a job-local shell and a writable `TMPDIR` on OHOS.
- The final source-built fallback recipe passed OHOS real-device `conan create`, upstream `make check` (33/33), and `test_package`; see `2.0.2/reports/upstream-tests.md`.

## Dependencies

- ncurses

## References

- https://github.com/mptre/pick
- https://github.com/mptre/pick/releases/tag/v2.0.2
