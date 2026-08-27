# DRAFT - Objective-C runtime consumer closure for gnustep-base on OHOS

> Contributor: xuguowei | Status: DRAFT | Created: 2026-08-27

## Scope

Use this pattern when a Conan package exposes GNUstep Foundation APIs on OHOS.
It is based on gnustep-base 1.31.1, where downstream users such as gnustep-gui
and affiche need a working Objective-C Foundation consumer, not just a packaged
shared object.

## Symptom

Incomplete recipes tend to fail in one of these ways:

```text
Foundation/Foundation.h: file not found
undefined reference to objc_msg_lookup
cannot find -lobjc
undefined reference to NSConstantString
symbol lookup error: libgnustep-base.so
```

A C-only smoke test can miss all of these problems because it does not compile
Objective-C syntax, create Foundation objects, or exercise message dispatch.

## Root Cause

GNUstep Base is compiled for the GNU Objective-C runtime used by `libobjc2` on
this stack. Downstream objects must use matching compile and link flags. In
particular, Objective-C consumers need the GNU runtime selection, Blocks support,
and the GNUstep constant string class. They also need the runtime library path
for `libgnustep-base`, `libobjc`, `libffi`, and the selected URL stack at target
execution time.

Conan dependency metadata will publish include and library directories, but it
will not invent the Objective-C ABI flags for consumers unless the recipe puts
them in `package_info()`.

## Recommended Solution

For `gnustep-base`, publish a complete consumer contract:

1. Keep `libobjc2`, `libffi`, and `curl` as transitive requirements.
2. Export `Library/Headers` and `Library/Libraries` as the public include and
   library directories.
3. Publish `gnustep-base` as the public library and expose the Conan target
   name `gnustep-base::gnustep-base`.
4. Add `-fobjc-runtime=gcc`, `-fblocks`, and
   `-fconstant-string-class=NSConstantString` to consumer compile flags.
5. Add `-fobjc-runtime=gcc` and `-fblocks` to executable and shared link flags.
6. Add GNUstep Base and dependency libdirs to both build and run environments.
7. Validate the recipe with an Objective-C `test_package` that imports
   `Foundation/Foundation.h`, constructs `NSString`, `NSArray`, `NSData`, and
   `NSDictionary` values, links the executable, and runs it on the OHOS target.

If a downstream build system ignores Conan cpp_info flags, inject the same flags
there as a consumer-side bridge, but keep the base package metadata authoritative.

## Verification

The gnustep-base 1.31.1 `test_package` compiled and executed during shadow CI:

```text
run_root=/storage/Users/currentUser/ohpc-ci-shadow/gnustep-shadow-state/runs/447d960d1462-20260825T192834Z-run-5127
L1_RESULT=pass: test_package executed
```

The test imports Foundation and exercises real Objective-C object creation,
which proves the package is consumable by the next GNUstep layer.

## Forbidden Shortcuts

- Do not replace the Objective-C `test_package` with a C-only link test.
- Do not rely on a system `libobjc` or system Foundation headers.
- Do not omit `-fobjc-runtime=gcc` from consumer compile and link metadata.
- Do not omit `-fconstant-string-class=NSConstantString` from Objective-C
  consumer compile flags.
- Do not mark the library adapted until a target-side consumer executable runs
  with the required runtime library path.
