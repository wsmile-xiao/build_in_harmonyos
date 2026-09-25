# SOCI

SOCI is a C++ **database access layer**: one API over several backends, with
`into`/`use` bindings, rowset iteration, prepared statement reuse and stored
procedure calls.

- Upstream: https://github.com/SOCI/soci
- Release: 4.1.4
- License: BSL-1.0 (Boost Software License 1.0)
- Build system: CMake
- Package form: `libsoci_core.a` plus one library per enabled backend
  (`libsoci_sqlite3.a`, `libsoci_empty.a`) and the headers under `include/soci/`

## Enabled backends

This package builds **SQLite3** (no server needed, and the backend the tests
use with `:memory:`) and **Empty** (a do-nothing backend used to exercise the
core).  DB2, Firebird, MySQL, ODBC, Oracle and PostgreSQL are explicitly
disabled — each needs a proprietary client library or a live database server.

## Dependencies

`sqlite3` (SQLite3 backend) and `fmt`.  Upstream vendors fmt as a git submodule
under `3rdparty/fmt`, which a GitHub archive tarball does not contain; the
recipe therefore depends on Conan's fmt and sets `SOCI_FMT_BUILTIN=OFF` so a
missing fmt fails loudly instead of silently falling back.

## HarmonyOS PC adaptation

**No patches.**  The adaptation is configuration: which backends are enabled
(see above) and where fmt comes from.

## Upstream tests

SOCI's own Catch2 suite (Catch is vendored in `tests/`).  With the two enabled
backends, ctest registers two tests — one per backend.  The SQLite3 binary
reports, in this configuration:

```
All tests passed (2242 assertions in 84 test cases)
```

Note the count: the sources contain 112 `TEST_CASE` lines, but only 84 run —
`tests/common/test-boost.cpp` is entirely inside `#ifdef SOCI_HAVE_BOOST` and
this build has no Boost.  The number reported here is Catch2's own runtime
count.

See `4.1.4/notes.md` and `4.1.4/test_package/MANIFEST.yml` for the full record.
