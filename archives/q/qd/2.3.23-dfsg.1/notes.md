# qd 2.3.23-dfsg.1 adaptation notes

- Upstream source is the Debian repacked original tarball `qd_2.3.23+dfsg.1.orig.tar.xz`
  (the dfsg.1 repack of qd 2.3.23). The historical LBNL `mpdist` download path
  (`crd-legacy.lbl.gov/~dhbailey/mpdist/`) now redirects to the `cs.lbl.gov` landing
  page and `davidhbailey.com/dhbpapers/qd-2.3.23.tar.gz` returns 404, so the Debian
  pool is the reproducible source for this version; the archive is byte-verified by
  the SHA256 in `conandata.yml`. The top-level directory inside the tarball is
  `qd-2.3.23+dfsg.1`; Conan's `get(..., strip_root=True)` strips it, and the
  package version string `2.3.23-dfsg.1` keeps the branch-naming form.
- The project uses Autotools with a pre-generated `configure` and bundled libtool
  helpers (`config/ltmain.sh`, `test-driver`), so no `autoreconf`/automake is needed.
  The bundled `config.guess`/`config.sub` are from 2021-01 and already accept the
  `aarch64-unknown-linux-gnu` triple that is passed explicitly for OHOS builds,
  therefore no config.sub patch is required.
- Two portability patches:
  1. lowers the umask used for the autoconf temp directory (`./confXXXXXX`) from
     077 to 022: directories created with mode 0700 are not writable afterwards on
     the setgid HMDFS filesystem (the directory owner is mapped to a shared
     owner), which made `config.status` abort with
     `can't create ./confXXXXXX/subs1.awk: Permission denied`.
  2. stops building/installing `docs/qd.pdf`: upstream lists it in
     `BUILT_SOURCES`, so `make all` builds it first via `make -C docs qd.pdf`,
     which fails both because the Conan out-of-tree build directory has no
     `docs/` and because neither the device nor the CI worker has LaTeX. The
     installed documentation remains `README` (the texinfo/eps sources stay in
     `dist_noinst_DATA`).
- qd has no third-party dependencies: only the C++ standard library and `libm`
  (`AC_CHECK_LIB(m,sqrt)`). The Fortran interfaces are disabled deterministically
  with `--disable-fortran` (upstream default is `auto`, which would enable them if
  any Fortran compiler happened to be present).
- The x86 FPU control-word fix is guarded by the host triple (`i?86/x86_64` only),
  so on aarch64 `fpu_fix_start`/`fpu_fix_end` are no-ops and the test suite runs as-is.
- `make check` is invoked during `build()`. It runs `qd_test` (8 cases for dd_real
  plus 8 for qd_real), `pslq_test` (5 dd_real plus 6 qd_real PSLQ cases), and
  `c_test` (Salamin-Brent pi case; informational, always exits 0) — 28 cases on
  the default invocation; running `./pslq_test -all` adds the 2 double-precision
  PSLQ variants, giving a complete inventory of 30 cases, all executed on the
  device. The `quadt_test`/`huge`/`qd_timer` binaries are `EXTRA_PROGRAMS`, i.e.
  upstream never registers them in `TESTS`, so they are not part of the run
  contract and are not counted.
- The consumer test links the installed `qd` library, asserts arithmetic roundtrips,
  the exact `dd_real::_eps` (2^-104) and `qd_real::_eps` (2^-209) fingerprints, pi
  digits, the C interface `c_qd_pi` components, and `qd-config --version` output.
