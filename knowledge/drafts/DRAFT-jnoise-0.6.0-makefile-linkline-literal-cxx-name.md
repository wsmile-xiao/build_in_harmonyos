# Draft: compiler name in the Makefile recipe *command position* - `make CXX=` cannot override it

Counterpart of `knowledge/drafts/DRAFT-jnoise-0.6.0-makefile-linkline-literal-cxx-name.kv`.
Source package: `archives/j/jnoise/0.6.0` (patch `patches/0001-source-Makefile.patch`).

## Problem

`jnoise-0.6.0/source/Makefile` links with the compiler **name written as a literal in the
command position** of the recipe:

```make
jnoise:   $(JNOISE_O)
	g++ $(LDFLAGS) -o $@ $(JNOISE_O) $(LDLIBS)
```

There is no `CXX := g++` (or `LD := g++`) assignment anywhere in that file, so nothing
references `$(CXX)` in the failing rule. The implicit compile rule *does* use `$(CXX)`,
which makes the failure deceptive: compilation succeeds and only the last step blows up.

OpenHarmony PC ships clang/clang++ only (`/data/service/hnp/bin`); `command -v g++` is
empty (RC=1) - there is no `g++` on the whole filesystem.

## Why the usual overrides do not work

Controlled reproduction on the OHOS builder (GNU make + toybox sh), `Makefile` reduced to
`all:` / TAB `g++ -v`, executed as `make -j1 CXX=clang++`:

```
g++ -v
make: g++: No such file or directory
make: *** [Makefile:2: all] Error 127
```

The command-line assignment was accepted, reached the make variables - and changed nothing,
because the recipe text never reads them. The same holds for `export CXX=clang++`.

Two verbatim error shapes were measured, both from this mechanism:

| shape | when | text |
|---|---|---|
| make execs the recipe directly (no shell metacharacters) | `make -j1 CXX=clang++` probe above | `make: g++: No such file or directory` + `Error 127` |
| command driven by the shell | `sh -c "g++ --version"` on toybox sh | `sh: g++: inaccessible or not found` |

Note: `archives/j/jnoise/0.6.0/notes.md` (first pass) paraphrased the symptom as
`/bin/sh: g++: not found`; that exact string is **not** reproducible on this builder and is
deliberately left out of `error_signature`.

## Fix

One portability patch, in the same file that also parameterises `install`:

```diff
-	g++ $(LDFLAGS) -o $@ $(JNOISE_O) $(LDLIBS)
+	$(CXX) $(LDFLAGS) -o $@ $(JNOISE_O) $(LDLIBS)
```

plus `INSTALL ?= /bin/install` for the bare `install` recipes (E174 family), and the recipe
passes the profile compiler on the make command line (`-j1` is mandatory on HMDFS workers):

```
make -C source -j1 PREFIX=/ CXX="/data/service/hnp/bin/clang++" jnoise
make -C source -j1 PREFIX=/ DESTDIR=<package_folder> CXX="/data/service/hnp/bin/clang++" install
```

Discriminator to apply **before** the first build:

```
grep -nE '^[[:space:]]+(g\+\+|gcc|cc)[[:space:]]' source/Makefile
```

A hit means command-position literal => patch required; no hit but `CXX := g++` present means
the variable family (command-line overridable).

## Verification (this package)

- `python3 scripts/ohc-run.py conan-verify jnoise 0.6.0` -> `G1: PASS`, `G2: PASS`, `G3: PASS`,
  `✅ 配方验证通过: jnoise 0.6.0` (`~/tmp/uc2/z32-jnoise/verify2.log`).
- Link line in the create log now execs the profile compiler:
  `/data/service/hnp/bin/clang++ -L... -o jnoise jnoise.o rngen.o -ljack -lrt`
  (`archives/j/jnoise/0.6.0/reports/conan-create.log:106`).
- `conan test` -> `RESULT: pass=6 fail=0`, RC=0 (`~/tmp/uc2/z32-jnoise/conantest.log`).
- Probe kept at `~/tmp/uc2/z32-jnoise/mkprobe/Makefile` for re-runs.

## Applicability / counter-examples

- Applies: raw-Makefile C/C++ projects (no configure, no CMake) that exec the compiler by name.
- Counter-example: `cohomcalg 0.32` uses `CC := g++` / `LD := g++` - same "no g++" symptom, but
  `:=` is still overridable from the make command line, so `make -j1 CC=clang++ LD=clang++`
  suffices and **no patch is needed**.
- Counter-example: configure/CMake projects - env/prefix override (`-DCMAKE_CXX_COMPILER`),
  not this family.

## Relations (referenced by file name; E-numbers are reused inside this directory)

- `knowledge/drafts/DRAFT-cohomcalg-0.32-makefile-gxx-override.kv` - same symptom family,
  **different layer**: variable assignment (overridable) vs command-position literal
  (not overridable). Different handling => new entry, not a duplicate.
- `knowledge/graph/E174.kv` (`knowledge/doc/E174.md`) - "make: install: No such file or
  directory", i.e. a bare `install` in the command position. Same *shape* of defect
  (command name resolved against a PATH that lacks it) but different phase
  (installation vs linking) and different remedy (parameterise to an absolute path vs
  parameterise to a profile variable).
- `knowledge/graph/E053.kv` - configure-time `CXX` env override; not applicable here.

## Records

- success_count: 1, fail_count: 0, confidence: 0.8
- contributor: 主理-32 (jnoise/0.6.0 first OHOS adaptation)
