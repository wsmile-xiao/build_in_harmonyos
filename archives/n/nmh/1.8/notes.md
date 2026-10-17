# nmh 1.8 - adaptation notes (feat/nmh-1.8, PR replacing #7809)

## Outcome

`conan create` builds nmh 1.8 for aarch64 OHOS: configure -> make ->
make install into a staging root, 46 bin/ commands, 14 libexec/nmh
helpers, etc/nmh samples, share/man.  Local package smoke and
functional tests pass 58/58.

## History - what made the previous attempt (PR #7809, 31 red runs) fail

1. `./configure` never got past the mandatory termlib probe
   ("Could not find setupterm in any library"): OHOS has no system
   termcap/curses, and conan ncurses only ships libncursesw.a while
   nmh probes -ltermcap/-ltinfo/-lcurses/-lncurses.
   -> requires ncurses/6.6 + private libncurses.a alias (copy of
   libncursesw.a) in a dedicated -L directory.
2. A hand-written ncursesw "stub" (empty functions) reached compile
   stage but produced broken behaviour and real compile errors.
   -> real ncurses library instead of stubs.
3. ndbm autodetect hard-fails configure ("could not find a working
   ndbm library/header combination"); OHOS (bionic) has no ndbm.h and
   gdbm/1.24 publishes without the gdbm compat layer.
   -> requires gdbm/1.24 + ndbmcompat/ndbm.h mapping the classic
   dbm_open/dbm_fetch/dbm_store/dbm_close/... API onto gdbm_*
   (GDBM_NOLOCK because slocal does its own fcntl locking).
4. HMDFS/sandbox details:
   - sandboxed bash/clang cannot getcwd() below the HMDFS conan
     cache; the whole configure/make/install runs on a real-fs copy
     under /data/storage/el2/base/.conan-build-nmh-1.8-<hash>/
     (same strategy as ncurses/6.6).
   - bionic only declares memmem() with _GNU_SOURCE.
   - install-time hard links for command aliases are denied by the
     filesystem; 0002 switches Makefile.in `LN` to `cp -f`.
5. config.sub (2022-05-25) does not know the `ohos` OS; 0001 teaches
   it the `ohos` / `linux-ohos` names (config.guess is bypassed by
   passing --build/--host explicitly).

## Runtime notes

- Commands read $HOME/.mh_profile (or $MH) and the transport config
  from compile-time /etc/nmh/mts.conf.  MHMTSCONF overrides the mts
  config path, so fully configured runs only need a profile with a
  `path:` entry plus MHMTSCONF pointing at the packaged mts.conf.
- test_package sets up a scratch HOME/MH profile and runs every
  installed command (-version), then a realistic folder workflow
  (scan/pick/folder/mark/flist/packf/rmm) and negative paths.

## Upstream tests

nmh ships 119 automake TESTS shell scripts (test/*/test-*).  `make
check` installs nmh into the compile-time /bin and /libexec/nmh
locations which do not exist in the sandbox, so it was not executed
here; the covered command behaviours are reproduced programmatically
(see test_package/MANIFEST.yml).

## CI source fetch

During the 2026-09 savannah.gnu.org gateway outage (HTTP 502) the CI
worker cannot reach download.savannah.gnu.org and the injected tuna
mirror does not carry nmh.  conandata.yml therefore lists both
Savannah hosts, `download-mirror.savannah.gnu.org` first - it is the
canonical redirect target of download.savannah.gnu.org and serves the
identical bytes (same sha256) but a different (healthy) gateway.

