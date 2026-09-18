# libcapi20

`libcapi20` is a user space implementation of the **CAPI 2.0** interface (Common
ISDN Application Programming Interface) used by telephony applications.  The
core library (`libcapi20.so.3`) talks to the hardware through loadable driver
modules (`lib/capi/lib_capi_mod_*.so`): `standard` (kernel CAPI), `fritzbox`
(AVM FRITZ!Box over TCP) and `rcapi` (remote CAPI).

## Versions

| Version | Status | Notes |
| --- | --- | --- |
| 3.27 | built | HarmonyOS PC (aarch64) adaptation, 3 portability patches, 21 assertions across 2 test executables |

Homepage: https://github.com/leggewie-DM/libcapi20

## HarmonyOS adaptation

- Consumed with `-lcapi20`; the driver plugins are `dlopen()`-ed at run time.
- Upstream hard-codes the compile time `LIBDIR` as the module directory.  A
  Conan package lives in an arbitrary prefix, so patch `0003` adds the
  `CAPI20_MODULE_DIR` override; the recipe exports it through `runenv_info`
  (`<package>/lib/capi`) so consumers work without extra configuration.
- `compat/byteswap.h` depended on glibc-only headers and was made
  self-contained (patch `0002`).
- `configure` probes a `umask 077` temp directory, which HMDFS cannot honour
  (patch `0001`).
- Upstream ships no test suite; the adaptation adds the consumer tests.
