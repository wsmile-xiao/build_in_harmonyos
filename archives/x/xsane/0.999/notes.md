# xsane 0.999 adaptation notes

## Status

`enabled on OHOS` — the GTK+ 2 blocker is resolved: the repository now carries
a native `gtk2/2.24.33` package (real `gtk+-2.0.pc`, GtkObject/GdkGC-era
headers), and this recipe requires it directly. The previous
`ConanInvalidConfiguration` guard and the `gtk+-2.0` -> `gtk+-3.0` alias shim
are retired; xsane's sources compile against actual GTK 2 headers.

## W0 dependency check

- Dependency count: 2 runtime + 2 build tools.
- Satisfied in repo: `sane-backends/1.2.1` (published to the artifact
  registry), `gtk2/2.24.33` (adapted in its own branch/PR — the dependency
  this recipe was unblocked by), `autotools-dev/20240727.1-nmu1`,
  `pkgconf/3.0.5`.
- The historical probe is `pkg-config gtk+-2.0 >= 2.0.0`; the gtk2 package's
  `pkg_config_name` is `gtk+-2.0`, so no alias is generated.
- Note for CI sequencing (R36): `gtk2/2.24.33` must publish before this
  package's CI gate can pass the registry-availability check.

## Source audit

- Upstream: https://gitlab.com/sane-project/frontend/xsane, tag `0.999`.
- Source URL:
  `https://gitlab.com/sane-project/frontend/xsane/-/archive/0.999/xsane-0.999.tar.gz`
- SHA256:
  `05359707effe1547ff123bb34443a95a4c54bd4888b91a3556c69875b64989b6`
  (re-verified by fresh download during local pre-validation).
- Build system: historical Autotools snapshot (`configure.in` + generated
  `configure` + `Makefile.in`); no CMake/Meson, no test suite at all
  (no `check:`/`test:` targets).
- The release tree ships no `config.guess`/`config.sub`; the recipe stages
  them from `autotools-dev` before `configure`.
- License: GPL-2.0-or-later (`xsane.COPYING`).
- Single archive root `xsane-0.999/` → `strip_root=True` verified against the
  real archive.

## Recipe design

- URL/SHA256 are inlined in `conanfile.py`; there is deliberately no
  `conandata.yml`, so the CI pre-download/rewrite branch is never entered
  (same approach as the xmodem 0.4.7.1 recipe).
- Optional image features stay off: `--disable-sanetest --disable-gtktest
  --disable-nls --disable-gimp --disable-jpeg --disable-png --disable-tiff
  --disable-lcms`.
- `PkgConfigDeps` alone satisfies the historical `gtk+-2.0` probe: the gtk2
  package declares `pkg_config_name "gtk+-2.0"`; `pkgconf` is forced as
  `PKG_CONFIG`.
- OHOS path: `/system/bin/sh` as CONFIG_SHELL/SHELL, package-local `TMPDIR`
  (OHOS `/tmp` is read-only), `umask 000`, an `mktemp` wrapper that recreates
  `-d` results via same-path `mkdir` (the device fs denies writes into 0700
  mktemp dirs whose group/other bits are all zero and silently ignores chmod
  there — recreate-from-mkdir makes the mode bits inherit instead), and
  llvm-ar/nm/ranlib/strip discovery.
- No `validate()` guard remains: the recipe builds for OHOS.

## Test situation

- Upstream tests: 0 (no automated test suite exists upstream — recorded
  honestly in `test_package/MANIFEST.yml`).
- test_package: `test_xsane.py` performs 4 deterministic assertions against
  the installed binary. CORRECTED against the real device (2026-09-14): the
  earlier claim that `--version` "exits 0 before GTK initialisation" is
  false — xsane's argument handling runs after GTK init, so headless targets
  exit 1 with "cannot open display". The headless smoke therefore asserts
  that the run REACHES GTK display init (proving the whole dynamic-linking
  chain loads); version output is asserted only on X-server targets (R40).

## Validation history

- True-device `conan create` (shadow, earlier round): configure passed, `lib/`
  compiled, then `src/xsane-back-gtk.c` failed against GTK 3 headers on the
  GTK 2-only types listed above. Device identifier withheld from committed
  notes; see the round report for the sanitized evidence.
- **2026-09-14, device full chain GREEN** (shadow job
  `xsane-0.999-shadow-20260914`, conan-home reused from the gtk2 job):
  14 build attempts iterated to green. Fix sequence, each device-fed:
  1. depend on native `gtk2/2.24.33`, retire the gtk+-3.0 alias and the
     OHOS `validate()` guard;
  2. port gtk2's configure-tmpdir patch (umask 000 + `${TMPDIR:-.}`) —
     the mktemp wrapper alone cannot reach the tmpdir code embedded in
     `config.status`;
  3. gettext pass-through stub for `bind_textdomain_codeset` (unreferenced
     guard under `--disable-nls`, no libintl on OHOS);
  4. stub injected at the END of `src/Makefile`'s LIBS (a command-line
     LDFLAGS override wipes AutotoolsDeps' `-L` paths, and a static archive
     placed before the objects is never pulled);
  5. `mkinstalldirs` invoked via `/system/bin/sh` (shebang signature policy);
  6. headless-honest smoke assertions (see Test situation).
  Final run: 30/30 packages installed (gtk2 stack from cache), package +
  sign OK, consumer smoke 3/3 passed.

## Local verification (this round)

- `python -m py_compile` on both `conanfile.py` files and `test_xsane.py`: pass.
- YAML parse of `manifest.yaml` and `test_package/MANIFEST.yml`: pass.
- SHA256 of a fresh source download matches the recipe constant: pass.
- `conan export archives/x/xsane/0.999` (Conan 2.32.0, isolated venv): pass,
  recipe loads and exports as `xsane/0.999#d5dbe182d7c8a7e94af4c85968408810`.
- `validate()` executed directly with a stubbed settings object: raises
  `ConanInvalidConfiguration` for `os=OHOS`, no raise for non-OHOS: pass.
- `test_xsane.py` executed against a stub binary printing `xsane 0.999`:
  4/4 assertions pass (the real binary path stays untested until a successful
  OHOS build).
- `git diff --check`: clean; changed files limited to
  `archives/x/xsane/0.999/**` plus two `knowledge/drafts/` files.
- Dependency existence on origin/main verified via `git ls-tree`:
  `sane-backends/1.2.1`, `gtk/3.24.43`, `autotools-dev/20240727.1-nmu1`,
  `pkgconf/3.0.5` all present.
- Not executed locally: full `conan create` (needs the repo Conan remotes and
  an OHOS toolchain; the OHOS path also fails fast by design, see Status).

## Next steps

1. `cairo/1.18.4.1` (xlib variant) must publish first — gtk2's PR CI blocks
   on it (R36); the task-hall task for it is in progress (xlib enabled).
2. After gtk2 merges and publishes, this package's CI gate clears the same
   way; run `ci/conan/build_and_test.sh` for the full L0-L5 gate at that
   point (the L0k `commands.json` for xsane is already committed).
3. GUI/runtime verification beyond display-init (scanner dialog, SANE scan
   path) needs an X-server target; boundary annotated per R40.
