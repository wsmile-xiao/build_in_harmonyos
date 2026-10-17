# lcmaps-plugins-jobrep

The LCMAPS **Jobrepository** plugin stores credentials and the resulting account
mappings into a relational database. LCMAPS keeps the current mapping state
between credentials and Unix accounts; this plugin preserves that state in a
database so it can be queried by other systems (e.g. GridSAFE) and give an
easily-backed-up historical view of the mapping state.

- Upstream: https://wiki.nikhef.nl/grid/LCMAPS
- Release: 1.5.8
- License: Apache-2.0 (per the `LICENSE` file the tarball ships)
- Build system: autotools
- Package form: a runtime-loadable LCMAPS plugin, not an ordinary link library —
  `lib/lcmaps/liblcmaps_jobrep.so` plus the `lib/lcmaps/lcmaps_jobrep.mod`
  symlink that LCMAPS resolves. The SQL schema files are installed under
  `share/jobrepository/sql/`.

## What the plugin is

LCMAPS loads it at run time and calls the five entry points declared in
`lcmaps/lcmaps_plugin_prototypes.h`:

| Entry point | Role |
|---|---|
| `plugin_initialize` | parse `--dsn` / `--username` / `--password` / `--odbcini` / `--test` |
| `plugin_introspect` | advertise 3 arguments: `user_dn`, `px509_chain`, `job_request` |
| `plugin_run` | gather credentials and write the mapping (needs a live database) |
| `plugin_verify` | same checks as `plugin_run`, without side effects |
| `plugin_terminate` | release internal configuration |

The database is reached through ODBC, and X.509 material is parsed with OpenSSL.
The plugin's `Makefile.am` deliberately leaves `liblcmaps_jobrep_la_LIBADD`
commented out, so the `lcmaps_*` and OpenSSL symbols stay undefined inside the
`.so` and are supplied by the host LCMAPS process.

## Dependencies

| Package | Why |
|---|---|
| `lcmaps/1.6.7` | `AC_LCMAPS_INTERFACE([basic])` — hard-fails without it |
| `unixodbc/2.3.12` | `PKG_CHECK_MODULES([UNIXODBC], [unixODBC])`, with an `-lodbc` + `sql.h` fallback |
| `openssl/3.5.6` | `AC_CHECK_LIB([crypto], [X509_free])` |

> `lcmaps` itself must be published to the registry first (R36). It is adapted
> in this repository at `archives/l/lcmaps/1.6.7/` as the **without-GSI**
> flavour; see that archive for the reasoning and the reduced-functionality
> declaration.

## HarmonyOS PC adaptation

Three portability patches; the plugin sources themselves are untouched.

| Patch | Purpose |
|---|---|
| `0001-config-guess-ohos.patch` | `uname -s` returns `HarmonyOS` on the target, absent from the shipped 2023-06-23 script — configure aborts at "checking build system type" (E007) |
| `0002-config-sub-ohos.patch` | learn the `ohos-linux` triplet, the `ohos*` OS entry and the `linux-ohos` kernel-os pair (E007) |
| `0003-configure-umask.patch` | create the config.status temp dir with `umask 022` instead of `077` (on OHOS HMDFS a 0700 dir is not writable by its own owner — E011) |

All three are POSIX-compatible edits; no `__OHOS__` platform macro is
introduced (R8 / preflight PF5).

### Do not use `AutotoolsDeps` here (E467)

`AutotoolsDeps` exports the whole dependency closure into the global `LIBS`
variable. autoconf's very first `AC_PROG_CC` "whether we are cross compiling"
probe inherits `LIBS`, so a probe that should only run an empty `main()` ends up
linking `-lodbc`/`-llcmaps_without_gsi`/`-lcrypto`, and the conftest cannot be
loaded at run time (no rpath into the Conan cache). configure then aborts with
`cannot run C compiled programs` before any real check runs. The recipe instead
injects `-I`/`-L` only, which keeps the early probe free of the closure while
the later header and `AC_CHECK_LIB` checks still succeed. Precedent:
`archives/c/cyrus-sasl-gs2/2.1.28`.

### Ancillary script not shipped

`utils/` installs `jobrep-admin` via `sbin_SCRIPTS` (Conan maps `sbindir` onto
`bin/`). It is a thin wrapper around the `mysql` client command, which is
neither a dependency of this package nor available on OHOS, so `package()`
removes `bin/` and `package_info()` declares empty `bindirs` — matching the
convention used by `archives/u/unixodbc/2.3.12`,
`archives/l/libiodbc2/3.52.16` and `archives/c/canl-c/3.0.0`. The SQL schema
files remain in `share/jobrepository/sql/` so an administrator can apply them by
hand.

## Upstream tests

None. `Makefile.am` has no `TESTS` and no `check_PROGRAMS` anywhere in the tree,
so `make check` is an empty no-op. `src/jobrep/jobrep_test.c` only appears in
`EXTRA_DIST` (the source-distribution list) — no target builds it, it hard-codes
its test identity, and it needs a GSI proxy plus a live database.

The package therefore ships a consumer test instead
(`1.5.8/test_package/test_jobrep.c`): it links `liblcmaps_jobrep` and makes real
calls to `plugin_initialize`, `plugin_introspect` and `plugin_terminate`,
asserting return codes and the advertised argument table — 10 assertions.
`plugin_run`/`plugin_verify` are not called: they need a live ODBC data source
and an X.509 credential chain.

See `1.5.8/notes.md` for the full record and `1.5.8/test_package/MANIFEST.yml`
for the test census evidence.
