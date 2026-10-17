# opusfile

Conan packaging for the high-level Ogg Opus decoding and seeking library.

## HarmonyOS PC adaptation

- Version: `0.12`
- Build system: Autotools
- HTTP/HTTPS support: enabled through `libopusurl`
- Dependencies: `libogg/1.3.5`, `opus/1.5.2.1`, and `openssl/3.5.6`
- Outputs: `libopusfile` and `libopusurl`, in shared or static form

The bundled platform scripts are patched to recognize the
`aarch64-unknown-linux-ohos` tuple. Shared OHOS builds use real unversioned
`libopusfile.so` and `libopusurl.so` files.

The upstream release registers no test entry. Its two example programs are
build examples requiring external input, not registered tests. The Conan
consumer is one independent integration entry and is counted once across
shared and static builds.
