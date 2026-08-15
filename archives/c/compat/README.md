# compat

Emacs Lisp compatibility library for newer Emacs APIs on older Emacs
versions.

## Version

- `31.0.0.2`

## Package Layout

The package installs the upstream Lisp files under:

- `share/emacs/site-lisp/compat-31.0.0.2`

It exports `COMPAT_LISPDIR` and prepends that directory to `EMACSLOADPATH` in
both Conan build and run environments so downstream Emacs Lisp packages can
load it in batch mode.

## Validation

The `31.0.0.2` recipe runs upstream `make compile`, `make test`, and
`make check` with `emacs/29.1` during `build()`. The `test_package` then runs a
real consumer `emacs -Q --batch` load check from the packaged Lisp directory.

OHOS validation run
`codex-a-compat-31.0.0.2-r13-20260803-140029-24622` passed with 221/223
upstream ERT tests passed, 2 skipped for the OHOS mock TRAMP `/tmp` limitation,
0 unexpected results, `make check` passed, and `test_package` passed.
