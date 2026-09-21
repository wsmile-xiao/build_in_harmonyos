# xelb 0.20

## Summary

`xelb` (X protocol Emacs Lisp Binding) is a pure Elisp implementation of the
X11 protocol built from the XCB project's XML descriptions. It exposes an
object-oriented API for X messages (requests, replies, events, errors) over
Emacs' asynchronous network connections and underpins EXWM.

The package installs 46 `*.el` sources plus their byte-compiled `*.elc`
under `share/emacs/site-lisp/xelb-0.20/` and `LICENSE` under `licenses/`.

## Source

- Official upstream: `https://github.com/emacs-exwm/xelb` (tag `0.20`)
- Release archive: `https://github.com/emacs-exwm/xelb/archive/refs/tags/0.20.tar.gz`
- SHA256: `7bbf6bdd84767d8f73b8d22421cd0a707669cc2cd4a9b2e85f6c81139e8a9296`
  (verified by downloading the tag tarball; byte-identical size 143475 with
  the Debian orig record)
- Archive contents: 54 entries — 47 `.el` files (46 libraries + `xelb-test.el`),
  `Makefile`, `xelb-gen` generator, `README.md`, `LICENSE`, ignore files
- License: GPL-3.0-or-later
- `Package-Requires: ((emacs "27.1") (compat "29.1"))`, bumped to compat 30 at
  release; both are covered by the Conan requirements `emacs/29.1` and
  `compat/31.0.0.2` (backwards compatible supersets)

## Build approach

The upstream `Makefile` only regenerates the protocol bindings from
xcb-proto XML (`all: clean $(LIBS)` via `./xelb-gen`). Running it inside the
recipe would delete the shipped pre-generated `xcb-*.el` files and add an
xcb-proto dependency, so — like the GNU ELPA install and the repository's
other Emacs Lisp recipes (`delight`, `ol-notmuch`, `web-mode`) — the recipe
byte-compiles the 46 shipped library sources directly with the packaged
Emacs and the compat load path:

```sh
emacs -Q --batch -L <compat-lispdir> -L . -f batch-byte-compile <46 .el files>
```

Every produced `.elc` must exist and be non-empty, otherwise `build()` fails.

## Tests

Upstream ships exactly one test module, `xelb-test.el`, with 2 ERT tests
(`xelb-test-binary32`, `xelb-test-binary64`) covering the binary32/binary64
conversion primitives of `xcb-types.el`. They are pure computations and need
no X server. `build()` runs them after byte-compilation:

```sh
emacs -Q --batch -L <compat-lispdir> -L . -l xcb.el -l xelb.el \
  -l xelb-test.el -f ert-run-tests-batch-and-exit
```

The ERT summary line (`Ran 2 tests, 2 results as expected`) is parsed from
the log file and reported as `HMBS_UPSTREAM_TEST_RESULT` (framework `ert`,
single deterministic source, no stdout counting).

The `test_package` validates the installed package from a consumer's point
of view (`sh test_xelb.sh`):

- `XELB_LISPDIR` is defined and contains the packaged artifacts;
- `EMACSLOADPATH` contains `XELB_LISPDIR`;
- `emacs -Q --batch -L $XELB_LISPDIR -l test_xelb.el` requires `xcb`/`xelb`
  from the packaged directory and runs 10 checks: packaged load path,
  both features, the four conversion primitives, float32/float64 1.0 round
  trips against the IEEE-754 bit patterns, and `xcb-xproto` loading.
  The final `XELB-RESULT: passed=10 total=10` line is parsed into
  `HMBS_TEST_PACKAGE_RESULT`.

## OHOS notes

No native code is compiled; the package is architecture independent
(`package_id()` is cleared). The only platform requirement is the packaged
`emacs/29.1` batch executable plus the `compat/31.0.0.2` lisp directory.

## Dependencies

- `emacs/29.1` (batch byte-compilation and ERT runner)
- `compat/31.0.0.2` (`xcb-types.el` does `(require 'compat)`; `xcb.el` uses
  `compat-call`)
- `ncurses/6.5#69914b9d115a9d31e4b32372c44e49bf` (`override=True` only, no new
  dependency: pins the transitive ncurses edge from `emacs/29.1` to the
  ohpcd-published recipe revision so preflight, which checks conancenter
  first, cannot resolve the bare version to the CCI ncurses recipe whose
  `pkgconf -> meson -> ninja/1.13.2` tool chain fails to build from source on
  OHOS with `System is unknown to cmake`. RREV recorded in
  `archives/e/emacs/29.1/notes.md`, 2026-08-09 isolated ohpcd run. The pin is
  version-preserving, so the published `emacs/29.1` OHOS binary stays valid.)
