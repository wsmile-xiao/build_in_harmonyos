# E546 — A header using sig_atomic_t must include <signal.h>

Status: DRAFT  
Source: ircd-hybrid 8.2.46-dfsg.1, HarmonyOS PC aarch64 adaptation  
PR: local branch `feat/ircd-hybrid-8.2.46-dfsg.1` (not submitted)

## 相关既有条目

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E420 | Legacy C calls dependency APIs whose declarations moved out of a neighboring header; add the dependency header that owns those APIs. | E420 concerns dependency API declarations and implicit-int pointer conversion. This case concerns a POSIX type used by a project-owned header, where the header contract itself omits its standard owner include. |
| E721 draft | OHOS musl `<dirent.h>` does not transitively expose `NAME_MAX` from `<limits.h>`; add the standard header at the source use site. | E721 covers a macro used by a C source file. This case covers a typedef used by a project header and adds a direct-header-first compile check to detect include-order masking. |
| E634 draft | Porting legacy BSD signal APIs and using `volatile sig_atomic_t` correctly in signal handlers. | E634 covers signal API availability and handler semantics; it does not cover the missing declaration header for `sig_atomic_t`. |

The knowledge engine was run on the compiler signature and returned E367, which concerns `Dl_info` in `dlfcn.h`. That is a false positive from generic “unknown type name” terms, not coverage of this failure. Exact searches for `sig_atomic_t` found no formal entry.

## Scope

C and C++ projects with an owned header that uses a POSIX type or declaration without including the standard header that owns it. The problem becomes visible when a libc header set or translation-unit include order stops providing the type incidentally through unrelated includes. It is not specific to ircd-hybrid or one compiler.

## Symptom

The HarmonyOS Clang build of ircd-hybrid stopped while compiling code that included `src/ircd_signal.h`:

```text
error: unknown type name 'sig_atomic_t'
```

The header used `sig_atomic_t` but did not include `<signal.h>`. The package notes record this OHOS build failure; patch `0002-ircd-signal-header-include.patch` adds the missing include.

## Root Cause

`sig_atomic_t` is declared by `<signal.h>`. C headers may include other headers for their own needs, but consumers cannot rely on an unrelated header to expose this typedef transitively. That accidental dependency can differ across libc implementations or disappear when a translation unit's include order changes.

Because the type appears in `ircd_signal.h`, adding `<signal.h>` only to one current `.c` file is insufficient: another translation unit can include `ircd_signal.h` first and fail. The owning header must state its own dependency.

## Recommended Fix / Workaround

Add the standard owner header directly to the project header:

```c
#include <signal.h>
```

For ircd-hybrid this is the unconditional one-line change in `src/ircd_signal.h`, carried by `patches/0002-ircd-signal-header-include.patch`. It is portable and requires no platform macro, compiler flag, or local typedef.

## Fallback

If the upstream header cannot be changed, include `<signal.h>` before it in every consuming translation unit. Treat this as temporary: it preserves an order-sensitive header contract and can miss future consumers.

## Forbidden Approaches

- Do not typedef or macro-define `sig_atomic_t`; that may diverge from the target libc's signal-safe type.
- Do not add a global `-include signal.h` flag; it masks the broken header for this build but does not fix consumers.
- Do not add an OHOS-only conditional around a standard header. The owner header is required independently of platform.

## Verification

In the extracted source tree, compile the project header as the first include using the same OHOS compiler and include flags from the package build:

```sh
printf '#include "src/ircd_signal.h"\nint main(void) { return 0; }\n' |
  ${CC:-clang} ${CPPFLAGS} -x c -fsyntax-only -
```

Without patch 0002, the observed type-name error is reproduced; with the include, the header is self-contained. The full Conan package build then compiles production translation units. On the HarmonyOS 6.1.0.117 aarch64 device, the final Conan create succeeded and the consumer test passed 3/3, including module loading, an IRC loopback NICK/USER, 001 welcome, PING/PONG, and clean SIGTERM shutdown.

## Prevention

For headers containing POSIX types, compile a minimal translation unit that includes each project header first. This catches missing owner headers hidden by broad umbrella headers in the normal build order.

## References

- `archives/i/ircd-hybrid/8.2.46-dfsg.1/notes.md`
- `archives/i/ircd-hybrid/8.2.46-dfsg.1/patches/0002-ircd-signal-header-include.patch`
- Similar but not equivalent: E420, E721 draft, E634 draft
