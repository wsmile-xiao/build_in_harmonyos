# shfm

`shfm` is a single-file file manager written in POSIX shell
(upstream: <https://github.com/dylanaraps/shfm>, MIT). Nothing is compiled:
the Conan package installs the script as `bin/shfm` and the upstream `LICENSE`.

Runtime requirements are a POSIX `sh`, a controlling terminal, and the POSIX
`[`, `printf`, `dd` and `stty` utilities, so there are no Conan dependencies.

The package carries one OHOS patch (see `0.4.2/notes.md`): on exit upstream
prints the final directory with `printf '%s\n' "$PWD" >&1` from an EXIT trap
while `main` is still redirected to `/dev/tty`. That works in dash only; in
mksh (the OHOS `/bin/sh`), bash and zsh the path went to the terminal and
`cd "$(shfm)"` received an empty string. The patch saves the caller's stdout as
fd 3 before the redirect and prints the path there.
