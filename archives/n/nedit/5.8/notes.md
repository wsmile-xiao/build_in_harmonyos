# nedit 5.8 adaptation notes

## Status

- Conan reference: `nedit/5.8`
- Branch: `feat/nedit-5.8`
- Package type: `application` (delivers `bin/nedit` and `bin/nedit-nc`)
- Current stage: recipe, manifests, notes, test_package and knowledge drafts written; OHOS build/test evidence is produced by the CI shadow runner.

## W0 dependency check

NEdit is a Motif/LessTif GUI text editor for X11. It has exactly one build
dependency, and it is a large one:

- `motif/2.3.8` — provides `libXm.so.4` plus the public Motif headers
  (`Xm/Xm.h`, `Xm/XmP.h`, ...). It already declares
  `libx11`, `libxt`, `libxext`, `libsm`, `libice` and `xorgproto` with
  `transitive_headers`/`transitive_libs`, so the entire X11 stack reaches this
  recipe through that single edge. `nedit` include path needs `Xm/` headers only;
  it does **not** use Xft, Xmu (no editres) or Xp.

There is no runtime dependency on any data file outside the package: the
application defaults ship inside the package (`share/X11/app-defaults/NEdit`)
and the built-in help text is compiled into the binary (`source/help_data.h`).

## Source and build audit

- URL:
  `https://downloads.sourceforge.net/project/nedit/nedit-source/nedit-5.8-src.tar.gz`
- SHA256:
  `5851aa7252dad952084529173640232562dec4a7c440209f196d53d4a5a8074d`
- Archive format: tar.gz, top directory `nedit-5.8/`
- License: GPL-2.0-or-later (`COPYRIGHT`)

Upstream ships a hand-written build system, *not* autotools:

```
Makefile                      # dispatcher only
makefiles/Makefile.linux      # CC/AR/CFLAGS/ARFLAGS/LIBS + include Makefile.common
util/Makefile.common          # libNUtil.a  (no .c.o rule: relies on make's builtin rule)
Xlt/Makefile.common           # libXlt.a
Microline/XmL/Makefile.common # libXmL.a
source/Makefile.common        # nedit nc
```

`Makefile` is a `.DEFAULT` dispatcher. Its recipe symlinks the selected
`makefiles/Makefile.<platform>` into each of the four sub-directories, runs the
four sub-makes, and then — as the last line — **executes the binary it just
linked** (`@source/nedit -V`).

That trailing execution is the single most important detail of this adaptation.
It must not happen inside `conan create` because the freshly linked `nedit` has
no rpath to the Conan-provided `libXm.so.4`; running it during the build would
abort the recipe with a loader error instead of a build error. The recipe
therefore reproduces the dispatcher's first step only (copy the platform
makefile into each sub-directory) and drives the four sub-makes directly, in
dependency order, target by target.

The second important detail is that all the make variables this recipe needs —
`CC`, `AR`, `ARFLAGS`, `CFLAGS`, `LIBS` — are assigned with plain `=` in
`makefiles/Makefile.linux`. Command-line assignments win over file assignments
in `make`, so passing them on the `make` invocation overrides upstream's
`cc`/`ar` and its `/usr/X11R6` paths without editing any upstream file.

### Files that are generated, not shipped

| File | Producer | How the recipe handles it |
|------|----------|---------------------------|
| `source/parse.c` | bison/yacc from `source/parse.y` | `source/parse_noyacc.c` is copied over it before building (upstream's documented fallback), so no yacc is needed |
| `source/help_topic.h`, `source/help_data.h` | `doc/setext` from `doc/help.etx` | already shipped pre-generated in the tarball |
| `doc/nedit.man`, `doc/nc.man` | `pod2man` from `doc/*.pod` | generated in `build()` via `make -C doc man`, best-effort (see decision 8) |

## HarmonyOS build decisions

1. **`-DUSE_DIRENT` is mandatory.** `util/printUtils.c` does

   ```c
   #ifdef USE_DIRENT
   #include <dirent.h>
   #else
   #include <sys/dir.h>
   #endif
   ```

   glibc still ships `<sys/dir.h>` as a compatibility shim, which is why
   Debian's `debian/rules` can drop the define. musl — and therefore OHOS — does
   not, so the `#else` branch fails to compile with
   `fatal error: 'sys/dir.h' file not found`. `makefiles/Makefile.linux` already
   carries the define; the recipe re-states it explicitly so it survives any
   future CFLAGS override.

2. **`-DUSE_LPR_PRINT_CMD`** is kept, matching upstream's Linux default
   (`printUtils.c` otherwise falls back to the `lp` queue helpers).

3. **`-DHAVE__XMVERSIONSTRING` is deliberately NOT defined.** With it,
   `source/help.c` declares `extern char _XmVersionString[]` and relies on the
   Motif library exporting that private symbol; without it, help.c keeps its own
   static buffer:

   ```c
   #ifdef HAVE__XMVERSIONSTRING
   extern char _XmVersionString[];
   #else
   static char _XmVersionString[] = "unknown";
   #endif
   ```

   Debian defines it to print the *runtime* Motif version (`-DBUILD_UNTESTED_NEDIT
   -DHAVE__XMVERSIONSTRING`). The package declares Motif **2.3.8**, which
   `util/motif.c:GetMotifStability()` classifies as `MotifKnownGood`
   (`XmFullVersion == 200308` falls in the 2.2.3–2.3.8 "good" window), so the
   `-DBUILD_UNTESTED_NEDIT` escape hatch is not needed either. Not defining it
   avoids an unnecessary dependency on a private libXm symbol.

4. **`-ansi` is dropped**, matching Debian's tested `-std=gnu17`. The sources
   compile cleanly as C17.

5. **`parse.c` is pre-generated** by copying `source/parse_noyacc.c` before the
   build. `source/Makefile.common` has a `parse.c: parse.y` rule that would
   otherwise try `bison`, then `yacc`, then the fallback; doing the fallback up
   front is deterministic and removes the tool from the worker requirements.

6. **No `-lrt`.** The local knowledge base records that the OHOS libc provides
   `clock_gettime`; only `-lm` is added explicitly.

7. **The package is signed.** Both ELF files receive a `.codesign` section with
   `binary-sign-tool -inFile ... -selfSign 1` during `package()` when the target
   OS is OHOS; an unsigned ELF cannot be executed from the Conan package cache.

8. **Manual pages are attempted explicitly, and are best-effort.**
   `doc/Makefile:man` shells out to `pod2man`, which is a *Perl script*, not a
   compiled tool; upstream's own top-level build keeps `docs` out of the default
   target for exactly that reason ("users may not have Perl installed"). The
   recipe runs `make -C doc man VERSION="NEdit 5.8"` with `ignore_errors=True`
   and `package()` ships `share/man/man1/*` only when the pages were actually
   produced. Rationale: the two editors are the deliverable, and a worker
   without Perl must not fail an otherwise complete package over documentation.
   (`pod2man/6.0.2` does exist as a Conan tool package in this repository, but
   `doc/Makefile` calls a bare `pod2man` found through `PATH` and the packaged
   script is meant to be invoked as `perl pod2man`, so wiring it in would mean
   patching upstream's `doc/Makefile` — not worth it for two man pages.)

## Installed layout

```
bin/nedit                    # GUI editor
bin/nedit-nc                 # upstream `nc` X client, renamed as Debian does
share/X11/app-defaults/NEdit # application class NEdit
share/man/man1/nedit.1       # only when the worker has pod2man (best-effort)
share/man/man1/nedit-nc.1    # only when the worker has pod2man (best-effort)
share/doc/nedit/{README,ReleaseNotes,faq.txt}
licenses/COPYRIGHT
```

`package_info()` publishes `bindirs=["bin"]`, prepends `bin` to `PATH` and points
`XAPPLRESDIR` at `share/X11/app-defaults`, so an X session that runs under the
Conan run environment finds NEdit's resource defaults the same way a system
install would.

## Headless smoke test

`nedit` and `nc` both answer the version options *before* touching the display:

- `source/nedit.c` opens the display first, and only on failure falls into

  ```c
  /* Respond to -V or -version even if there is no display */
  for (i = 1; i < argc && strcmp(argv[i], "--"); i++)
      if (0 == strcmp(argv[i], "-V") || 0 == strcmp(argv[i], "-version")) {
          PrintVersion();
          exit(EXIT_SUCCESS);
      }
  ```

- `source/nc.c` processes the command line *before* `XtOpenDisplay` and exits
  from `processCommandLine()` on `-V`/`-version`.

`getBuildInfo()` (which `PrintVersion()` calls) is written to tolerate a NULL
display: the `Server:`/`Visual:` fields fall back to `<unknown>`. The recipe
exploits this to make the consumer test run on a worker with no X server and no
`DISPLAY` at all.

## Test package

`test_package/test_nedit.py` performs 31 consumer assertions on the installed
package. It is driven by the recipe's `test()` through the interpreter running
Conan (`sys.executable`), so the harness itself never depends on `/bin/sh`
(mksh on OHOS cannot execute ELF binaries) or on a `PATH` lookup.

Covered:

- both executables are present, are regular files and are executable;
- the ELF header of each says `EM_AARCH64` / `ET_DYN` (a real OHOS AArch64
  PIE binary, not a host leftover);
- `nedit -V` and `nedit -version` exit 0 with `DISPLAY` removed and print
  `NEdit 5.8`;
- `nedit-nc -V` and `nedit-nc -version` exit 0 with `DISPLAY` removed and print
  `Version 5.8`;
- the version output is not a stub: it contains the downstream-delivered
  `With Motif:` line, proving the Motif headers and the linked `libXm.so.4`
  agreed at build time;
- invoked with no display and no `-V`, `nedit` fails (non-zero exit) with
  `Can't open display` on stderr — i.e. it is genuinely an X/Motif client, and
  the version path above is a deliberate early answer rather than a program that
  never opens a display at all;
- `share/X11/app-defaults/NEdit` exists and is non-empty.

## Local verification

Performed on this Windows host:

- source archive downloaded and SHA256 checked against
  `5851aa7252dad952084529173640232562dec4a7c440209f196d53d4a5a8074d`;
- archive member list and the five makefiles (`Makefile`,
  `makefiles/Makefile.linux`, and the four `Makefile.common`) read line by line;
- `source/parse.y` / `parse_noyacc.c`, `util/printUtils.c`, `util/motif.c`,
  `source/help.c`, `source/nedit.c`, `source/nc.c`, `doc/Makefile` and
  `debian/rules` inspected to confirm every claim in these notes.

Not executable on this host:

- `conan create` for OHOS: no `ohos-aarch64` capable compiler is installed here
  (the profile's compiler lives at `/data/service/hnp/bin/clang`, which only
  exists on the CI worker), and a Windows host cannot execute OHOS AArch64 ELF
  files in any case;
- upstream tests: none exist (see `upstream_tests` in `manifest.yaml`).

## Next commands

Isolated shadow run:

```sh
CI_PACKAGES="archives/n/nedit/5.8" zsh ci/conan/build_and_test.sh
```

Direct isolated `conan create` on an OHOS worker:

```sh
cd archives/n/nedit/5.8
conan create . --build=missing \
  -s:h os=OHOS -s:h arch=armv8 \
  -s:h compiler=clang -s:h compiler.version=15 \
  -s:h compiler.libcxx=libc++ -s:h build_type=Release
```

## R38 command metadata

The package produces two CLI entry points, so the software-level
`archives/n/nedit/commands.json` is included and declares `nedit/5.8` as a tool.

## Knowledge drafts

Four paired drafts record the transferable parts of this adaptation:

- `knowledge/drafts/DRAFT-nedit-5.8-handwritten-makefile-dispatcher-and-dev-targets.{md,kv}`
- `knowledge/drafts/DRAFT-nedit-5.8-headless-smoke-test-for-motif-x11-apps.{md,kv}`
- `knowledge/drafts/DRAFT-nedit-5.8-use-dirent-musl-vs-distro-cflags.{md,kv}`
- `knowledge/drafts/DRAFT-nedit-5.8-generated-source-and-private-motif-symbol.{md,kv}`

They are draft candidates only; formal numbering and B-class recognition remain
a maintainer review decision.
