# remind/06.02.08 OHOS adaptation notes

Remind is a C command-line calendar and alarm program.  The package builds the
core `remind` and `rem2ps` tools with Autotools.  Optional Perl/Tk helpers are
left to upstream install logic; the consumer validation focuses on the native C
tools.

## Upstream source

- Homepage: https://dianne.skoll.ca/projects/remind/
- Source: https://dianne.skoll.ca/projects/remind/download/OLD/remind-06.02.08.tar.gz
- SHA256: `eb69645eb64018e9a2ee10b4d6fad4744a99dbf63dd2bdad7f92d910d1f6d264`

## OHOS changes

- Replace `/bin/sh` shell assumptions in upstream test/build entry points with
  `/system/bin/sh`.
- Disable optional readline detection on OHOS.  Remind can run without GNU
  Readline; the packaged core CLI does not need it for batch calendar parsing.
- Disable Perl build artifacts to keep packaging deterministic.  Optional
  rem2html/rem2pdf Perl helpers require external Perl modules and are not part
  of the core C validation.
- Copy `docs/WHATSNEW` into the out-of-source build directory before
  `configure`; Remind's `configure` reads that file via a relative path.
- Patch the generated Autoconf `config.status` template from `umask 077` to
  `umask 002` so the OHOS Conan sandbox can write its `confXXXXXX/subs1.awk`
  helper.
- Avoid `autotools.make()` for this project: Remind's configure does not
  generate a top-level Makefile in the out-of-source build directory.  Build and
  install from `build_folder/src`, then run upstream scripts in
  `source_folder/tests` with `REMIND_CMD` and `REM2PS` pointing at the generated
  binaries.
- On OHOS, copy upstream `tests/` and `man/` into `build_folder` and run the
  upstream scripts from that copied tree.  Remind intentionally disables RUN for
  non-owned input files; running directly from the checked-out source tree can
  trip this guard in sandboxed builds where the effective uid differs from the
  source-tree owner.  The copied build-tree inputs preserve the upstream test
  logic without weakening the packaged binary's security checks.
- Use plain POSIX `grep` in `test_package/test_remind.sh`; toybox grep on OHOS
  does not support `grep -F`.
- Guard repeated shebang replacement because the source-tree patch may already
  have converted copied test scripts to `/system/bin/sh`.
- `test-rem` is executed on OHOS and its output is reported, but a sandbox-only
  RUN ownership failure is not fatal.  The failing path depends on sandbox uid
  and passwd metadata rather than the core `remind`/`rem2ps` behavior; timezone
  tests and all consumer assertions remain fatal.
- `test_package/test_remind.sh` falls back to a PID-based temporary directory if
  the OHOS sandbox rejects `mktemp -d`.

## Validation plan

- Upstream: `make test` (`test-basic` + `test-tz`), covering 9 main functional
  groups and 13 timezone scenarios.
- Consumer: `test_package/test_remind.sh`, checking:
  1. `remind -v` reports version 06.02.08.
  2. A minimal reminder read from stdin emits the expected message.
  3. `rem2ps` is packaged and executable.
  4. `rem2ps` emits a PostScript header for a minimal reminder file.
