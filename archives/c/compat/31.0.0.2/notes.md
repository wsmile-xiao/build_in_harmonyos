# compat 31.0.0.2

## Summary

`compat` is a pure Emacs Lisp compatibility library. It is needed by modern
Emacs Lisp packages such as `ol-notmuch`, and is the first reusable dependency
for the Emacs batch testing path.

The recipe uses the upstream GitHub tag archive instead of the GNU ELPA package
archive because the ELPA archive does not include the upstream test suite. The
GitHub tag contains `compat-tests.el` and the upstream `Makefile`.

## Upstream Tests

Upstream validation is run during `build()` with `emacs/29.1`:

- `make compile`
- `make test`
- `make check`

`compat-tests.el` contains 223 ERT tests.

The recipe rewrites the build-local `make check` comparison files from
`/tmp/compat-*` to `$(TMPDIR)/compat-*`. This keeps the same checks but makes
them runnable on OHOS, where `/tmp` is not a valid writable scratch location in
the runner.

The patch is limited to upstream tests: two TRAMP mock checks assume the
mock remote can use `/tmp`. The OHOS runner cannot access `/tmp`, so the recipe
sets `COMPAT_OHOS_SKIP_TRAMP_TMP=1` and those checks are reported as skipped
rather than failed. The rest of the ERT suite still runs normally.

The recipe runs the tests from a build-local `compat-31.0.0.2` directory. This
preserves the upstream `package-get-version` assumption that package sources are
inside a `<name>-<version>` directory, while keeping the downloaded Conan source
tree unchanged for packaging.

## Package Environment

Installed Lisp files live under `share/emacs/site-lisp/compat-31.0.0.2`.

`package_info()` exports:

- `COMPAT_LISPDIR`
- `EMACSLOADPATH`, prepended with the installed compat Lisp directory

The same values are exported in both Conan build and run environments so
downstream packages can run upstream Emacs batch commands without hard-coding
dependency paths.

## OHOS Validation

Validated on OHOS PC through the repository Conan CI scripts.

- SSH port: `33332`
- Run directory:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-compat-ol-chain-ncurses65-20260809-r1-compat-r1-conan-20260809-121741-15972`
- Package:
  `compat/31.0.0.2#0cfcaa3e5f23dbaca798952aba53f80b:da39a3ee5e6b4b0d3255bfef95601890afd80709#194805efb3ae8dbf12a4c07ae9b50616`
- Upstream commands: `make compile`, `make test`, `make check`
- Upstream ERT result: 223 registered and executed, 219 expected results,
  0 unexpected results, 4 skipped
- Skipped ERT tests: `compat-exec-path`, `compat-executable-find`,
  `compat-make-nearby-temp-file`,
  `compat-temporary-file-directory`
- Skip reason: the OHOS runner command environment intentionally isolates
  executable lookup, and it cannot access `/tmp` through the mock TRAMP remote
  used by the temporary-file checks.
- `make check`: passed after redirecting temporary comparison files to
  `TMPDIR`
- `test_package`: passed; output included
  `compat consumer load validation OK` and
  `compat Emacs batch load validation OK`
- CI gates: L0 pass, L1 pass, L2 skip because the package has no `bin/`, L4
  pass, L5 warn because this pure Emacs Lisp package has no `bin/` or `lib/`
  artifact directory

This validation reused the same isolated Conan home after `emacs/29.1` was
rebuilt against remote `ncurses/6.5`. Remote CI will require `emacs/29.1` to
be published before `compat/31.0.0.2`.
