# org 9.8.8

## Summary

`org` is the GNU ELPA Org distribution. It is needed by `ol-notmuch` because
`ol-notmuch.el` requires Org link support and declares `org >= 9.8`.

The selected source is the official GNU ELPA package:

- URL: `https://elpa.gnu.org/packages/org-9.8.8.tar.lz`
- SHA256: `6a8c38a96476f9dbe8594f9e8209098840bc6ead099bebc4fb62ed20b6fff6c7`
- ELPA metadata: `org 9.8.8`, dependency `emacs >= 28.2`

The earlier `https://elpa.gnu.org/packages/org-9.8.8.tar` URL is no longer
served by GNU ELPA and caused release CI source-stage 404 failures. GNU ELPA
still lists and serves the official historical `org-9.8.8.tar.lz` package, so
the recipe downloads that archive explicitly. It first tries system `tar`; on
OHOS toybox `tar` cannot read lzip-compressed tarballs, so the recipe falls
back to a private `lzip` helper and then extracts the plain `.tar`.

## Upstream Tests

The GNU ELPA `org-9.8.8.tar.lz` package does not include the upstream Org test
suite. It does include generated `org-loaddefs.el` and `org-version.el`.

For this package, upstream tests are recorded as `not_run` rather than passed.
The recipe still runs an Emacs batch source-load smoke during `build()`:

```sh
emacs -Q --batch -L <source> --eval "(require 'org) ..."
```

That check verifies `org`, `ol`, `org-version`, and
`org-link-set-parameters` from the package source directory.

## Package Environment

Installed Lisp files live under:

```text
share/emacs/site-lisp/org-9.8.8
```

`package_info()` exports:

- `ORG_LISPDIR`
- `EMACSLOADPATH`, prepended with the packaged Org Lisp directory

This is required so downstream packages use Org 9.8.8 instead of any older Org
copy bundled with the Emacs executable.

## Consumer Validation

`test_package` runs:

```sh
emacs -Q --batch -L "$ORG_LISPDIR" -l test_org.el
```

The test verifies that `locate-library` resolves both `org` and `ol` from
`org-9.8.8`, then requires both libraries and checks:

- `(featurep 'org)`
- `(featurep 'ol)`
- `(org-version)` is `9.8.8`
- `org-link-set-parameters` is available
- built-in link parameters such as `https` are initialized

## OHOS Validation

Validated on OHOS PC through the repository Conan CI scripts.

- SSH port: `33332`
- Run directory:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-org-ol-chain-ncurses65-20260809-r1-org-r1-conan-20260809-121840-16673`
- Conan full reference:
  `org/9.8.8#7e3e705c579f41c186416425f5b87980:da39a3ee5e6b4b0d3255bfef95601890afd80709#e7773116854955820c4aa4c958e6fde0`
- Source-load smoke: passed; log contains
  `RUN: emacs -Q --batch -L <source> --eval ...`
- `test_package`: passed; output contains
  `org consumer load validation OK` and
  `org Emacs batch load validation OK`
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

This package unlocks the `org/lisp` part of the `ol-notmuch make lisp` load
path. The remaining minimum dependency is `notmuch-emacs` (`notmuch >= 0.39`).
