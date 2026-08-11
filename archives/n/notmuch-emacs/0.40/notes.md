# notmuch-emacs 0.40

## Summary

`notmuch-emacs` packages the Emacs Lisp front-end from the official Notmuch
0.40 release tarball. It is the `notmuch` Lisp feature needed by
`ol-notmuch`.

The selected source is the official Notmuch release:

- URL: `https://notmuchmail.org/releases/notmuch-0.40.tar.xz`
- SHA256: `4b4314bbf1c2029fdf793637e6c7bb15c1b1730d22be9aa04803c98c5bbc446f`
- Emacs package metadata: `notmuch 0.40`, dependency `emacs >= 25.1`

## Scope

This package intentionally does not build the native Notmuch CLI, library,
mail indexer, Ruby bindings, or Python bindings. It only packages the Emacs
Lisp front-end under `emacs/`.

That is enough to unlock the `notmuch/emacs` load-path dependency for
`ol-notmuch make lisp`. Runtime mail operations still require a matching
native `notmuch` executable outside this package.

## Upstream Build Checks

The release tarball has no standalone Emacs Lisp test directory. The recipe
therefore runs the upstream Emacs Lisp build checks that are available:

- generate `notmuch-version.el` and `notmuch-pkg.el` from upstream templates
- generate `notmuch-autoloads.el` with upstream `autoloads-gen.el`
- load `notmuch-version`, `notmuch-lib`, and `notmuch` via `emacs -Q --batch`
- byte compile all upstream Notmuch Emacs Lisp sources

These checks are build validation, not the full native Notmuch test suite.

## Package Environment

Installed Lisp files live under:

```text
share/emacs/site-lisp/notmuch-0.40
```

`package_info()` exports:

- `NOTMUCH_EMACS_LISPDIR`
- `EMACSLOADPATH`, prepended with the packaged Notmuch Emacs Lisp directory

## Consumer Validation

`test_package` runs:

```sh
emacs -Q --batch -L "$NOTMUCH_EMACS_LISPDIR" -l test_notmuch_emacs.el
```

The test verifies that `locate-library` resolves `notmuch` and `notmuch-lib`
from `notmuch-0.40`, then requires `notmuch-version`, `notmuch-lib`, and
`notmuch`, and checks:

- `notmuch-emacs-version` is `0.40`
- `(featurep 'notmuch-lib)`
- `(featurep 'notmuch)`
- command entry point `notmuch`
- command entry point `notmuch-search`

## OHOS Validation

Validated on OHOS PC through the repository Conan CI scripts.

- SSH port: `33332`
- Run directory:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-notmuch-emacs-ol-chain-ncurses65-20260809-r1-notmuch-emacs-r1-conan-20260809-122057-17554`
- Conan full reference:
  `notmuch-emacs/0.40#4738e977855ce34279a5ff5ccd3ae1e7:da39a3ee5e6b4b0d3255bfef95601890afd80709#1aba9f2cf4bab8a0e4b9fbb94b28fc82`
- Build checks: generated `notmuch-version.el`, `notmuch-pkg.el`, and
  `notmuch-autoloads.el`; loaded `notmuch-version`, `notmuch-lib`, and
  `notmuch`; byte compiled the upstream Emacs Lisp sources.
- Packaged artifacts: 26 `.el` files, 21 `.elc` files, one SVG logo, one
  desktop file, and README/data files.
- `test_package`: passed; output contains
  `notmuch-emacs consumer load validation OK` and
  `notmuch-emacs batch load validation OK`
- CI gates: L0 pass, L1 pass, L2 skip because the package has no `bin/`,
  L4 pass, L5 warn because this pure Emacs Lisp package has no `bin/` or
  `lib/` artifact directory.
- Validation reused the same isolated Conan home after `emacs/29.1` was
  rebuilt against remote `ncurses/6.5`. Remote CI still requires
  `emacs/29.1` to be published first.

## Dependency Status

This recipe depends on `emacs/29.1`. Local OHOS validation can proceed if the
isolated Conan cache already contains `emacs/29.1`. Remote CI will require
`emacs/29.1` to be published in the package registry first.

Once this package and `org/9.8.8` are available, the minimum load-path pieces
for `ol-notmuch make lisp` are present: `compat`, `org`, and `notmuch`.
