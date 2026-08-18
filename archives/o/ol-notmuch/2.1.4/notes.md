# ol-notmuch 2.1.4

## Summary

`ol-notmuch` is an Emacs Lisp extension that adds Org links to Notmuch
buffers. The package installs `ol-notmuch.el`, `ol-notmuch.elc`, generated
autoloads, the upstream `Makefile`, `README.org`, and `LICENSE`.

## Tests

The release tarball has no standalone test directory. Upstream validation is the
Makefile `lisp` target, which runs Emacs batch byte-compilation, autoload
generation, and `check-declare`.

The current recipe runs this upstream target during `build()` with packaged
dependencies:

```sh
make lisp EMACS=emacs LOAD_PATH="-L <compat> -L <org> -L <notmuch-emacs> -L <source>"
```

This executes the upstream Emacs batch byte-compile, autoload generation, and
`check-declare` flow. The `test_package` then verifies the installed package by
loading `compat`, `org`, `notmuch`, and `ol-notmuch` from the Conan-provided
load paths.

## OHOS notes

No native code is compiled. Runtime mail operations still require a target-side
Notmuch CLI/database; this package supplies the Emacs Lisp integration used by
Org links.

## New Port Validation

Date: 2026-08-09

Validated on the new OHOS device port `33332` with isolated job
`ol-chain-ncurses65-20260809-r1`.

- Run directory:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-ol-notmuch-ol-chain-ncurses65-20260809-r1-ol-notmuch-r1-conan-20260809-122331-18871`
- Command:
  `zsh ci/conan/build_and_test.sh archives/o/ol-notmuch/2.1.4`
- Result: `Build Summary` success, 1 package built, 0 failed
- Full package reference:
  `ol-notmuch/2.1.4#481f35d439ba12a6260fb4bbc610c500:da39a3ee5e6b4b0d3255bfef95601890afd80709#39cba90c099b29108ecd04f9b02cbb51`
- Gate summary:
  `L0=pass`, `L1=pass(test_package executed)`, `L2=skip(no bin/ dir)`,
  `L4=pass(no patches)`, `L5=warn(no bin/lib artifacts; share-only package)`
- Upstream validation result: `make lisp` passed. The log includes
  `RUN: make lisp EMACS=emacs LOAD_PATH=...` with packaged
  `compat-31.0.0.2`, `org-9.8.8`, and `notmuch-0.40` directories.
- Upstream checks passed: 3/3, covering Emacs batch byte-compilation,
  autoload generation, and `check-declare`.
- `test_package`: passed; output contains
  `ol-notmuch consumer load validation OK` and
  `ol-notmuch Emacs batch load validation OK`.
- Dependency chain in this isolated run:
  `ncurses/6.5` was downloaded from `ohpcd`; `emacs/29.1`,
  `compat/31.0.0.2`, `org/9.8.8`, and `notmuch-emacs/0.40` were built in
  order in the same isolated Conan home before `ol-notmuch`.
