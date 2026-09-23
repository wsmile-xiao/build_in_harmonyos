# miniupnpc 2.3.3.1 adaptation notes (upstream 2.3.3)

## Build environment

- Build system: CMake
- Source tag: `miniupnpc_2_3_3` (`bf4215a7574f88aa55859db9db00e3ae58cf42d6`)
- Compiler: clang 15.0.4
- Platform: HarmonyOS aarch64 (HongMeng Kernel 1.12.0)
- External dependencies: none

## Recipe decisions

The Conan recipe uses CMake, not the upstream Makefile. Static library output is
the default and shared output remains selectable through the `shared` option.
Samples are disabled by default.

`UPNPC_BUILD_TESTS=ON` is now set in `generate()`, and `build()` invokes
`cmake.test(cli_args=["--output-on-failure"])`. This runs the upstream suite
registered by `miniupnpc/CMakeLists.txt`.

## Upstream test inventory

CMake registers seven CTest cases:

1. `validateminixml`
2. `validateminiwget`
3. `validateupnpreplyparse`
4. `validateportlistingparse`
5. `validateigddescparse1`
6. `validateigddescparse2`
7. `validateaddr_is_reserved`

`validateminiwget` uses the bundled `minihttptestserver` over loopback. It does
not require an external UPnP device or Internet access. The two IGD cases use
different fixtures and are counted separately by CTest.

The Conan `test_package` links the installed library and calls
`ParseNameValue()` plus `GetValueFromNameValueList()` on an inline SOAP response,
so the consumer check is deterministic and does not depend on a gateway.

## Patches

No source patch is required.

## Verification status

Static recipe and manifest checks are complete. The updated recipe still needs a
clean `conan create` and CTest run on OpenDesk before the test result can be
marked passed; no test result is fabricated in `manifest.yaml`.

编译结束: 2026-09-13
最终状态: recipe-updated, OpenDesk verification pending
