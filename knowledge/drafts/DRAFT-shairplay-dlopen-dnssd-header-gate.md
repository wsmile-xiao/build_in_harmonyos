# Optional DNS-SD runtime must not require its header in the `dlopen` branch

In shairplay 0.9.0, `LT_LIB_DLLOAD` detects `dlopen`, yet `configure.ac` then requires `dns_sd.h`. On HarmonyOS PC, the probe reports “library containing dlopen: none required”, but the header is absent, so configuration stops before C compilation.

The actual source has two branches. With `HAVE_LIBDL`, `src/lib/dnssd.c` declares the DNS-SD ABI types it uses and opens `libdns_sd.so` at runtime. Without that branch, it includes `dns_sd.h` and needs the development header. Requiring the header when `dlopen` exists reverses these requirements.

The repair is to test the header only when **both** Libtool `dlopen` probes are negative. Do not invent a DNS-SD stub or suppress an actual missing-library error. Preserve `dnssd_init` returning `DNSSD_ERROR_LIBNOTFOUND` or `DNSSD_ERROR_PROCNOTFOUND` if the optional runtime cannot be loaded.

Verification on the HarmonyOS arm64 target: `conan create` compiled and packaged `libshairplay.so`, installed two public headers, ran `make check` (0 upstream-registered tests), then built and ran a consumer linked against the installed package; the consumer called `dnssd_init` and passed. Final W3 receipt chain: `shairplay-w3-20260929T121145Z`, 12/12 PASS/NOT_REQUIRED; log SHA-256 `39b466743707fb77e8d768a9220e5692446c5f6a93914ab41abe832070382dbd`.

Boundary: this pattern applies only when the dynamic-loader branch really provides all compile-time types and uses an explicit runtime error contract. If the application requires DNS-SD at runtime, it must still provide `libdns_sd.so` or a Conan dependency. Existing E160/DRAFT-E656 already cover the separate `config.guess` and Autotools timestamp failures; this draft contributes the header-gate boundary.
