# wv 1.2.9 Path B candidate evidence

## Application scope

- Task: `contrib-2910`
- Task branch: `feat/wv-1.2.9`
- Application path: Path A (base adaptation) + Path B (knowledge extension)
- Candidate draft: `knowledge/drafts/E336-draft-wv-libgsf-header-closure.{kv,md}`
- Path B result: subject to reviewer approval

The Path B claim is not based on patch size, elapsed time, or the number of CI
attempts. It is based on a reusable diagnosis for legacy C sources that rely on
dependency declarations being exposed through neighboring headers.

## Reusable problem

wv 1.2.9's `wvSummary.c` called libgsf metadata APIs without including the
header that owns their declarations. The compile command already contained the
correct libgsf include directory and the link graph already contained libgsf.
Adding include directories or changing Conan dependency traits therefore could
not repair this translation unit.

With the OHOS Clang 15 toolchain and upstream `-ansi` mode, the undeclared calls
were typed as legacy implicit `int` expressions. Pointer-returning APIs then
failed with `-Wint-conversion`:

```text
wvSummary.c:104:17: error: incompatible integer to pointer conversion
  initializing 'const GValue *' with an expression of type 'int'
wvSummary.c:146:21: error: incompatible integer to pointer conversion
  initializing 'GsfDocMetaData *' with an expression of type 'int'
```

The source-level repair adds the exact owning header:

```c
#include <gsf/gsf-doc-meta-data.h>
```

It does not suppress diagnostics, add private declarations, mutate libgsf, or
force an include globally.

## Same-source before/after evidence

The comparison uses wv 1.2.9 source SHA256
`4c730d3b325c0785450dd3a043eeb53e1518598c4f41f155558385dd2635c19d`,
libgsf 1.14.58, and the same OHOS Clang 15 toolchain.

| Evidence | Before | After |
|---|---|---|
| Runner | `codex-wv-r11-wv-wv-1.2.9-shadow-r11-20260821-215827-1266` | `codex-wv-r13-wv-wv-1.2.9-shadow-r13-20260821-221704-30316` |
| Relevant source delta | no direct metadata header | one direct metadata header |
| `wvSummary.o` | failed with 2 pointer conversion errors | compiled with 0 errors |
| `wvSummary` CLI | not linked | linked and installed |
| Package creation | not reached | completed |
| Later result | build stopped | advanced to independent test CMake discovery failure |

Shadow r12 is intentionally excluded from the functional comparison because it
failed while parsing an incomplete patch hunk and never compiled the source.

## Adaptation root-cause chain

The complete Path A work also isolated several independent OHOS build issues:

| Stage | Root cause | Scoped resolution |
|---|---|---|
| source retrieval | primary host was not reachable from the worker | retain primary URL and add a checksum-equivalent mirror |
| configure launch | generated script execution was restricted | invoke configure explicitly through `sh` |
| cross tools | Autotools did not consistently discover target binutils | derive SDK sibling tools from the profile compiler |
| pkg-config | worker pkgconf required its matching runtime library | expose a build-local runtime search path |
| config.status | `umask 077` helpers were inaccessible on HMDFS | use build-only `umask 022` output permissions |
| source compile | libgsf metadata declarations were not directly included | add the owning public header |
| consumer build | CMake was not initially discoverable on the worker | discover declared build tools for the test package |
| consumer metadata | public headers and libraries were not propagated | declare direct requirements and public Conan traits |

These common environment repairs support the difficulty record but are not
presented as new knowledge. E336 is deliberately limited to the direct-header
declaration problem.

## Duplicate boundary

- E081/E093: APIs missing from the target libc; wv's libgsf APIs exist.
- E309: generated public headers omitted from a package; the libgsf header was
  installed and already reachable.
- `DRAFT-conan-staticlib-transitive-headers`: Conan include-directory traits;
  r11 already had the libgsf include directory on the command line.
- E307: unavailable CMake in a test package; this was the later r13 failure,
  not the source compile failure.

The new rule is: when a dependency API exists but an old C source relies on
transitive declarations, include the public header that owns the API and prove
the repair with the same dependency graph. Do not weaken compiler diagnostics.

## Final validation

- Device: `currentUser@10.62.221.191:2222`
- Runner: `codex-wv-r18-wv-wv-1.2.9-shadow-r18-20260821-234825-21984`
- Runner result: `rc=0`
- Conan create: pass
- Consumer assertions: 3 passed, 0 failed
- L0/L1/L4/L5: pass
- L2: non-blocking skip because installed CLIs did not satisfy version/help probes
- Build Summary: Total 1, Success 1, Failed 0
- Package: `wv/1.2.9#66cd91e92991b63c66b81ca115a34fae:e2e9c2e2ac191f51e4f1e065fc93d0516a8b9a91#65123a5bfba4c59303953b28ba72dff3`

## Honest boundary

The upstream 1.2.9 release has no shipped testsuite. The Conan consumer has one
executable with three assertions covering public initialization APIs; it does
not parse a complete Word document. The evidence establishes the package build,
link, runtime consumer, and direct-header repair, but does not claim full parser
behavior or guarantee Path B approval.

## Change boundary

This task changes only `archives/w/wv/1.2.9/` and the directly related
`knowledge/drafts/E336-draft-wv-libgsf-header-closure.{kv,md}` files. It does
not modify dependency recipes, repository infrastructure, formal knowledge
entries, or another task's files.
