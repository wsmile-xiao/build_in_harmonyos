# GNU Prolog 1.5.0

The recipe builds the upstream `src` autotools project for OHOS armv8. It
disables optional line editing, sockets, documentation, HTML, examples, and
installation links because the package is consumed as a command-line compiler
and runtime. The upstream `make check` target remains enabled and runs all four
upstream test directories.
