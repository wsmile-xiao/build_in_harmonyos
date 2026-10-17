# delight 1.7

## Summary

`delight` is a single-file GNU ELPA package (author Phil Sainty) that
customises the mode names displayed in the mode line. For major modes it
rewrites the buffer-local `mode-name`; for minor modes it replaces the lighter
in `minor-mode-alist`, and it advises `format-mode-line` so that the original
name is still shown outside the mode line (e.g. in `describe-mode`).

The package installs `delight.el` and the byte-compiled `delight.elc` under
`share/emacs/site-lisp/delight-1.7/` and `COPYING` under `licenses/`.

## Source

- Official archive: `https://elpa.gnu.org/packages/delight-1.7.tar`
- SHA256: `92728eb388daf445ff6f73b152e2372f513b86ac1fd542bc6530e91341cefac8`
- Archive contents: `delight-1.7/{delight.el, delight-pkg.el, COPYING}`
- License: GPL-3.0-or-later
- `Package-Requires: ((cl-lib "0.5") (nadvice "0.3"))` — both are Emacs 24.3+
  built-ins, so the only Conan requirement is `emacs/29.1`.

## Tests

delight 1.7 has **no upstream test suite**. The release tarball contains only
`delight.el`, `delight-pkg.el` and `COPYING`; the upstream Savannah repository
contains only `COPYING` and `delight.el`; there is no Makefile, no test
directory, no ERT file and no CI configuration. The upstream test gate is
therefore recorded as `NO_UPSTREAM_TESTS` with discovery evidence.

Substitute upstream validation, run in `build()` with the packaged Emacs:

```sh
emacs -Q --batch -f batch-byte-compile delight.el
emacs -Q --batch -l delight.elc --eval "(unless (featurep 'delight) (error ...))"
```

The `test_package` then validates the installed package from a consumer's
point of view (`sh test_delight.sh`):

- `DELIGHT_LISPDIR` is defined and contains `delight.el` / `delight.elc`;
- `EMACSLOADPATH` contains `DELIGHT_LISPDIR`;
- `emacs -Q --batch -L $DELIGHT_LISPDIR -l test_delight.el` requires
  `delight` from the packaged directory and checks the public entry points,
  that the `format-mode-line` advice is installed, a minor-mode lighter
  rewrite (`abbrev-mode` -> `" Abv"`, including the "Toggle minor modes"
  menu label), a major-mode delight (`emacs-lisp-mode` -> `"Elisp"`) whose
  `mode-name` becomes `(delight-mode-name-inhibit ORIGINAL "Elisp")`, and
  that the around-advice binds `delight-mode-name-inhibit` to `t` by default
  while honouring an explicit `nil` binding. `format-mode-line` renders
  nothing in a batch session, so the advice is exercised directly rather than
  through rendered strings.

## OHOS notes

No native code is compiled; the package is architecture independent
(`package_id()` is cleared). The only platform requirement is the packaged
`emacs/29.1` batch executable.
