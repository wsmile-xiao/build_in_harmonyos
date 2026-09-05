# gnustep-gui 0.32.0 adaptation notes（路径 B 知识库扩展）

## W0 dependency check

Source package:

- URL: https://ftp.gnustep.org/pub/gnustep/core/gnustep-gui-0.32.0.tar.gz
- SHA256: `0c03a1b6313babd592ec58fcb825091f77eb27429a4ce4306ec3a7cfa7f9a1f6`

Direct dependencies selected for the first slice:

- `gnustep-base/1.31.1`
- `gnustep-make/2.9.2` as `tool_requires`
- `libtiff/4.7.2`
- `libjpeg/10`
- `libpng/1.6.58`

Upstream INSTALL marks TIFF as required and JPEG/PNG as recommended. GIF,
ImageMagick, ICU, aspell, sound, speech, speech recognition, and CUPS are kept
off for the first AppKit-enabling slice.

## Source/build analysis

The upstream package is a GNUstep AppKit library with:

- top-level `configure`
- top-level `GNUmakefile`
- `Source`, `Images`, `Sounds`, `Model`, `Tools`, `Panels`, `PrinterTypes`,
  `TextConverters`, `ColorPickers`, `KeyBindings`, `Resources`, `Printing`,
  `Themes`, and `Tests` subprojects

`configure` needs `GNUSTEP_MAKEFILES` from `gnustep-make`. It also needs
GNUstep Base headers/libraries available while building, so the recipe injects
the base package's `Library/Headers` and `Library/Libraries` paths into
`CPPFLAGS`, `LDFLAGS`, and `LD_LIBRARY_PATH`.

On HarmonyOS CI, the generated Autotools arguments can resolve `--build` and
`--host` to the same OHOS triplet. Upstream autoconf then treats configure as a
native build and tries to execute the unsigned `conftest`/`a.out` probe. The
recipe filters the generated triplet arguments for OHOS and forces
`--build=<cpu>-unknown-linux-gnu`, `--host=<cpu>-unknown-linux-ohos`, and
`--target=<cpu>-unknown-linux-ohos`, plus `ac_cv_prog_cc_works=yes`, before
calling configure through the selected shell.

`GSXibKeyedUnarchiver.m` uses GNUstep Base's `GNUSTEP_BASE_HAVE_LIBXML` macro
inside `#if` guards. On the current OHOS package graph, GNUstep Make exports the
macro as an empty command-line define (`-DGNUSTEP_BASE_HAVE_LIBXML=`), which is
not a valid preprocessor expression for clang. The source patch keeps upstream's
truthy behavior when the macro is `1`, while treating an empty or missing value
as `0`.

GNUstep GUI's recursive subprojects do not all inherit configure-time
`CPPFLAGS`. CI #34252 reached `Model/IMCustomObject.m` with only `/include`
and user-local GNUstep include paths, so `Foundation/NSObjCRuntime.h` from
`gnustep-base` was missing. `_gnustep_environment()` now exports GNUstep Make's
`ADDITIONAL_INCLUDE_DIRS` and `ADDITIONAL_LIB_DIRS` from the Conan
`gnustep-base` package folder. Keeping these as environment variables lets
subproject `+=` assignments preserve their own `-I../Headers` paths while also
adding the base closure.

The same recursive make environment also includes the public include/library
directories of transitive runtime dependencies such as `libobjc2`, because
GNUstep Base public headers include Objective-C runtime headers like
`objc/objc.h`.

GNUstep GUI's `Tools/GNUmakefile` builds Objective-C command-line tools such as
`make_services`, but it does not explicitly attach GNUstep Base/runtime link
libs. The recipe exports `ADDITIONAL_TOOL_LIBS` with the Conan-discovered
`gnustep-base` and `libobjc2` library names so those tools resolve Foundation
classes during link.

The `Tools` subproject also links against `-lgnustep-gui` while the library is
still in the build tree. On OHOS CI, GNUstep Make emitted only versioned shared
objects under the `Source` build output before the recursive tools build, so
`ld.lld` could not resolve the unversioned linker name. The recipe builds
`Source` first, creates `libgnustep-gui.so` plus compatible soname links beside
GNUstep Make's `libgnustep-gui.<version>.so` or `libgnustep-gui.so.<version>`
output and in `Source/obj`, then builds the remaining package subprojects in
top-level order. The same link normalization is repeated after install inside
the package library directory.

GNUstep GUI's tool preamble still carried explicit `-lgnustep-gui` entries for
`gpbs`, `set_show_service`, `gopen`, and `gcloseall`. On OHOS CI this fails
before install because the shared library's build-tree file is versioned and
may be placed below a GNUstep Make object subdirectory. The second source patch
switches those tools to the first matching in-tree `libgnustep-gui*.so*` alias
  under `$(GNUSTEP_SYSTEM_LIBRARIES)`, `../Source/$(GNUSTEP_OBJ_DIR)`, or
  `../Library/Libraries` for shared builds while keeping `-lgnustep-gui` as
  fallback and for static builds.

## Test package

`test_package` compiles a real Objective-C AppKit consumer. It creates
`NSImage`, `NSBezierPath`, and `NSColor` objects through `AppKit/AppKit.h`,
links against `gnustep-gui::gnustep-gui`, and runs the executable when the
target can run.

## Upstream test inventory

The release tarball contains a discoverable `Tests/` tree with:

- 30 Objective-C source test files
- 19 `TestInfo` files
- 2 `GNUmakefile` files

The discovered upstream inventory is recorded separately from the consumer
smoke test in `test_package/MANIFEST.yml`.

## Local validation

Prepared on Windows host only. Conan is not installed in this local desktop
environment, so `conan create` was not run here.

2026-08-29 follow-up validation passed: `py_compile` for recipe/test recipe,
YAML parse for package metadata, `git apply --check` for the XIB unarchiver
patch against upstream tag `gui-0_32_0`, and `git diff --check`.

## Path B knowledge drafts

- `knowledge/drafts/DRAFT-gnustep-gui-gnustep-env-closure.{kv,md}`
- `knowledge/drafts/DRAFT-gnustep-gui-appkit-consumer-closure.{kv,md}`
- `knowledge/drafts/DRAFT-gnustep-gui-upstream-test-inventory.{kv,md}`
- `knowledge/drafts/DRAFT-gnustep-gui-ohos-autoconf-cross-probe.{kv,md}`
- `knowledge/drafts/DRAFT-gnustep-gui-tool-link-discovery.{kv,md}`

## True-device shadow CI

- 2026-08-26: `gnustep-base/1.31.1` passed device shadow CI, so this recipe
  was updated to use the same GNU Objective-C runtime ABI and to propagate
  public dependency headers/libs to downstream consumers.
- `gnustep-gui` r1, r2, and r3 preflights passed. Heavy runs r1, r1-retry, r2,
  and r3
  stopped in L0 before configure/build while probing `gnustep-base/1.31.1` from `ohpcd`.
  Latest run: `/storage/Users/currentUser/ohpc-ci-shadow/gnustep-shadow-state/runs/128ebc19d9f3-20260826T081822Z-run-20021`.
- Worker stderr: `Connecting to remote 'ohpcd' anonymously ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`
- No GUI source build was executed in those heavy runs.
- 2026-08-29: PR CI #34102 reached `conan-build-test`; dependency resolution
  used `libpng/1.6.58`, but configure stopped at
  `configure: error: cannot run C compiled programs` after autoconf tried to
  run an unsigned C probe. The recipe now rewrites OHOS configure triplets to
  explicit cross mode before invoking configure.
- 2026-08-29: PR CI #34248 confirmed the configure triplet fix and entered
  `make`, then failed in `GSXibKeyedUnarchiver.m` because clang saw
  `#if GNUSTEP_BASE_HAVE_LIBXML` after the macro had been exported as an empty
  define. Added `patches/0001-guard-empty-gnustep-base-libxml-macro.patch` to
  make the guard accept empty or undefined values as false.
- 2026-08-29: PR CI #34252 passed the XIB macro guard and continued into the
  `Model` subproject, then failed on `IMCustomObject.m:28:10: fatal error:
  'Foundation/NSObjCRuntime.h' file not found`. Added recursive GNUstep Make
  `ADDITIONAL_INCLUDE_DIRS`/`ADDITIONAL_LIB_DIRS` environment values derived
  from `gnustep-base`.
- 2026-08-29: PR CI #34254 showed that passing `ADDITIONAL_INCLUDE_DIRS` as a
  make command-line variable overrides gnustep-gui subproject include additions
  and removed `-I../Headers`, causing `AppKit/AppKitDefines.h` to be missing.
  The base include/lib additions were moved into the build environment so
  GNUstep Make can append subproject-local include paths normally.
- 2026-08-29: PR CI #34256 preserved the AppKit include paths and then failed
  from `GNUstepBase/GSObjCRuntime.h:57:11: fatal error: 'objc/objc.h' file not
  found`. The recursive make environment now also appends include/lib paths for
  transitive runtime dependencies, including `libobjc2`.
- 2026-08-29: PR CI #34260 passed the recursive header path fixes and reached
  `Tools/make_services` link, then failed with undefined Foundation class
  symbols such as `__objc_class_name_NSString` and `__objc_class_name_NSBundle`.
  Added environment-level `ADDITIONAL_TOOL_LIBS` for `gnustep-base` and
  `libobjc2`.
- 2026-08-29: PR CI #34274 reached `Tools/set_show_service` and failed because
  `ld.lld` could not find `-lgnustep-gui` in the in-tree `Source` output. The
  build now runs `Source` first and creates unversioned/major-version shared
  library links before the tools subproject links against GUI.
- 2026-08-29: PR CI #34276 showed the initial link normalization only handled
  ELF-style `libgnustep-gui.so.<version>` names. GNUstep Make 2.9.2 defines the
  versioned shared library as `libgnustep-gui.<version>.so`, so the recipe now
  recognizes both patterns when creating the in-tree linker name. It also keeps
  the follow-up build on the remaining subprojects instead of re-entering
  `Source` through the top-level aggregate target.
- 2026-08-29: PR CI #34283 still failed in `Tools/set_show_service` with
  `ld.lld: error: unable to find library -lgnustep-gui`. Added
  `patches/0002-link-tools-with-in-tree-gui-library.patch` so shared tool links
  consume the already-built versioned library file directly from `Source`.
- 2026-08-29: PR CI #34284 stopped at `apply_conandata_patches()` because the
  first `0002` hunk carried too much release-file context. The patch was
  reduced to anchor on the unique `*_TOOL_LIBS += -lgnustep-gui` lines.
- 2026-08-29: PR CI #34287 showed the no-context `0002` hunk still was not
  accepted by Conan's patch application path. The patch now keeps one stable
  context line before and after the four tool link assignments.
- 2026-08-29: PR CI #34289 applied `0002`, but a direct
  `../Source/./obj/libgnustep-gui.0.32.0.so` path still missed the actual
  build output. The tool patch now uses `$(wildcard ...)`/`$(firstword ...)` to
  find the generated in-tree `libgnustep-gui*.so*` file below `../Source`.
- 2026-08-29: PR CI #34300 still expanded the shared tool link back to
  `-lgnustep-gui`, so no matching unversioned linker file was visible from
  `Tools` at link time. The recipe now stages `Source` outputs into
  `Source/obj` and the package library directory, adds the package library
  directory to recursive GNUstep Make link flags, broadens shared-library
  candidate detection, and copies cross-dir library aliases instead of creating
  package symlinks to build-tree files.
- 2026-08-29: PR CI #34304 showed `make install` was still targeting `/include`
  because GNUstep Make needs `GNUSTEP_HEADERS`, `GNUSTEP_SYSTEM_LIBRARY`,
  `GNUSTEP_SYSTEM_HEADERS`, and `GNUSTEP_SYSTEM_LIBRARIES` in addition to
  `GNUSTEP_SYSTEM_ROOT`. The recipe now exports those paths to the package
  folder and recognizes versioned `libgnustep-gui.0.32.0`-style outputs
  without a `.so` suffix.
- 2026-08-29: PR CI #34307 confirmed the remaining tool-link fallback still
  missed the no-suffix `libgnustep-gui.0.32.0` build artifact. The tool patch
  now uses `find -type f` to locate the versioned in-tree library file before
  falling back to the older `.so*` patterns.
- 2026-08-29: PR CI #34319 still fell back to `-lgnustep-gui` during the Tools
  link step. The build now runs `Source` with `install` before the remaining
  package subprojects so GNUstep Make materializes the shared library into
  `Library/Libraries`, then re-stages the library aliases for the in-tree tool
  lookup.
- 2026-08-29: PR CI #34341 then failed in `install` because GNUstep Make does
  not create nested `Library/Headers/AppKit`, `Library/Headers/Cocoa`, and
  `Library/Libraries/gnustep-gui/Versions/0.32/Resources` directories on its
  own. The recipe now pre-creates the expected headers, pkgconfig, and
  resources targets before the install pass.
- 2026-08-29: PR CI #34347 then reached `Tools/set_show_service` and failed
  again on `-lgnustep-gui`. The recipe now stages the Source shared-library
  aliases once after the plain Source build and again after Source install, so
  the `Tools` link step can see `libgnustep-gui*` even if install rewrites the
  build tree.
- 2026-08-29: PR CI #34352 still fell back to `-lgnustep-gui` because the
  in-tree search was too strict about regular files. The tool preamble now
  accepts symlinked GNUstep GUI build artifacts as valid candidates too.
- 2026-08-29: follow-up local fix broadens the shared tool lookup to accept
  plain `libgnustep-gui`, `libgnustep-gui.so`, and versioned variants from
  both `Source/obj` and `Library/Libraries` via `wildcard`, keeping
  `-lgnustep-gui` only as the final fallback.
- 2026-08-29: the shared-library staging helper now also treats plain
  `libgnustep-gui` and `libgnustep-gui.so` build outputs as candidates, so the
  staged aliases can reach `Source/obj` and `Library/Libraries` before Tools
  links.
- 2026-08-29: latest CI still showed a bare `-lgnustep-gui` token surviving
  through `SYSTEM_LIBS`, so the recipe now rewrites `Tools/GNUmakefile.preamble`
  directly as a fallback, then passes the exact staged GUI library path to
  `Tools` as `GNUSTEP_GUI_TOOL_LIBS=<path>` after recursively preferring
  staged versioned/shared aliases, and filters the raw basename from inherited
  system libs for the four tool targets.
- 2026-08-30: PR CI #34482 moved past the previous bare-`-lgnustep-gui` stage
  but failed in `Tools/set_show_service` because the recipe still picked the
  package `Library/Libraries/libgnustep-gui.so` alias before the build-tree
  `Source/obj` copy. The tool-library lookup now prefers the in-tree
  `Source/obj` alias first, leaving `Library/Libraries` only as a fallback.
- 2026-09-02: PR CI `#36637` passed. The recipe now runs `Tests/GNUmakefile`
  `check` in runnable environments, so the upstream GUI test inventory is
  exercised as `51/51` alongside the `test_package` smoke test.

Regenerate the shadow tar/wrapper from the current branch and rerun heavy after
`gnustep-base/1.31.1` is published/queryable in `ohpcd` or the worker registry policy is fixed.

## Next commands

```sh
conan download "gnustep-base/1.31.1" -r=ohpcd --only-recipe
conan download "libtiff/4.7.2" -r=ohpcd --only-recipe
conan download "libjpeg/10" -r=ohpcd --only-recipe
conan download "libpng/1.6.58" -r=ohpcd --only-recipe
CI_PACKAGES="archives/g/gnustep-gui/0.32.0" zsh ci/conan/build_and_test.sh
```
