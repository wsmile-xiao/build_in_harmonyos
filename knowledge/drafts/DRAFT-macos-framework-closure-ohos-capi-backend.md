# DRAFT - macOS framework-bound closure on OHOS: contract-anchored reimplementation with a native C API backend

> Status: DRAFT | Source: archives/c/cliclick/5.1 (closure-unsatisfiable instance); family instances synergy-core 1.20.4 and screenresolution 1.6 (E240). Final Exxx numbering is assigned by the knowledge-base editor.

## Rule

When upstream sources are bound to desktop-only frameworks (Objective-C /
Cocoa / Carbon / CoreGraphics / CGEvent) and the OHOS sysroot provides no
ObjC runtime (no `objc` headers, no `libobjc`), the dependency closure is
unsatisfiable. Decide the route by family practice, not by reflex:

1. Cross-platform projects grow an OHOS native backend on their existing
   platform abstraction.
2. Partially portable CLIs keep the portable core, add an OHOS backend and
   split capabilities with negative tests.
3. Fully framework-bound sources are kept in-tree uncompiled for provenance
   while the observable CLI contract is reimplemented in portable C anchored
   by the upstream test suite, with an OHOS native C API backend and honest
   capability split.

GNUstep is a fallback closure, never the default route.

This entry is deliberately a family-level pattern. Narrowing it to "100% ObjC
-> pure C rewrite" leaves a single instance and dissolves the cross-library
basis of the entry.

## Blocking surface (dependency-closure domain)

The failure is compile/link class, provable with three self-contained probes
(no run artifacts needed):

```sh
test ! -e /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/objc && echo no-objc-headers
ls /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/lib/aarch64-linux-ohos | grep -i objc ; echo no-libobjc-above
printf '#import <Foundation/Foundation.h>\nint main(void){return 0;}\n' > probe_objc.m
/data/service/hnp/bin/clang --target=aarch64-linux-ohos \
  --sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot \
  -fsyntax-only probe_objc.m
# expected: fatal error: 'Foundation/Foundation.h' file not found
```

All three verified on device 2026-09-09: `objc` headers absent, no `objc`
match in the sysroot lib directory, Foundation import fails to compile. Any
source set that imports such frameworks cannot close its dependency closure
on OHOS.

## Family statement (three instances; cite each correctly)

1. **synergy-core 1.20.4 — cross-platform instance, native-backend
   injection consumer.** Patches 0004/0027/0028/0042 add the OHOS platform
   layer; 0027 creates `src/lib/platform/OHOSKeyState.cpp` including
   `<multimodalinput/oh_input_manager.h>`. Cite it as a native-backend
   injection-consumer practice. Do NOT cite it as a "closure unsatisfiable"
   case: it is a cross-platform application whose OHOS backend was not forced
   by a macOS framework closure.
2. **screenresolution 1.6 (E240) — partially portable CLI instance.**
   CoreGraphics read-only display queries moved onto
   `OH_NativeDisplayManager` with capability split and negative tests.
3. **cliclick 5.1 — closure fully unsatisfiable instance.** 100% ObjC CLI;
   macOS sources stay in-tree uncompiled; the CLI contract is pinned 1:1 by
   the upstream test suite (58 portable assertions ported verbatim, 2
   platform-blocked assertions replaced with a named reason) and
   reimplemented in pure C over `OH_Input_*` / `oh_key_code.h` /
   `OH_NativeDisplayManager` with command-level capability split.

## Contract anchoring method

- Probe the sysroot first; only then pick the tier (toolchain facts, not
  platform-name assumptions).
- Keep the upstream test suite as the oracle: portable assertions 1:1,
  platform-blocked assertions replaced only with a named reason and cause.
- Upstream desktop sources stay in the delivered tree uncompiled (provenance).
- New backend code is additive (for example `ohos/` sources plus one recipe
  patch), never a rewrite of upstream files.
- Every capability boundary gets an explicit unsupported diagnostic plus a
  negative test — never silent stubs.

## Fallback: GNUstep substitute closure (honest tradeoff)

`libobjc2` + `gnustep-base`/`gnustep-gui` can substitute parts of the ObjC
runtime closure when the ObjC sources themselves must execute. Honest
tradeoffs: it is a heavyweight new dependency closure on OHOS; headless and
service behavior is uncertain; and the CGEvent/Carbon injection layer still
needs a full re-host, so most of the porting work remains. Use it only as a
fallback, never as the default route for small CLIs — for those, the
contract-anchored reimplementation is cheaper and fully testable.

## Anti-patterns (forbid)

1. Deleting upstream macOS sources from the delivered tree to "clean up" —
   provenance violation, the port becomes unauditable against upstream.
2. Shipping silent stubs without negative tests — fakes the platform
   capability boundary and defers failures to production.
3. Treating GNUstep as the default route — partial closure substitute that
   multiplies work for a CLI whose contract is small and testable.

## Principle hooks (match-level honesty)

- `P-TOOLCHAIN-001` — the closure verdict must come from probing sysroot
  contents (LLVM toolchain SDK facts), not from platform-name assumptions.
- `P-SYSCALL-001` — a missing desktop framework closure is a platform
  difference that build flags cannot bypass; it forces source-level
  re-implementation/native backends.
- `P-RUNTIME-001` — capabilities outside the real API surface must be
  intercepted before invocation with explicit diagnostics plus negative
  tests, never mid-run failures.
- Match honesty: these are the nearest existing principles; the
  capability-split facet itself could justify a future dedicated principle
  (decision left to the knowledge-base editors, not invented here).

## Related

- `E240` — same family (native display backend + capability split); this
  entry adds the route decision when the closure is fully unsatisfiable, the
  contract-anchoring method, and the GNUstep fallback tradeoff. E240 covers
  neither, so the two entries coexist via `similar_to` without overlap.
- synergy-core 1.20.4 patches — recipe-tree practice instances (not knowledge
  entries); `gnustep-*` recipes exist in archives but are not knowledge
  entries and did not yield a second closure-unsatisfiable instance, which is
  exactly why the family-level wording is mandatory.
