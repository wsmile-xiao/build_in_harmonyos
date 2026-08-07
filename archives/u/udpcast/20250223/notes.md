# UDPcast 20250223 adaptation notes

## Build configuration

- Build system: Autotools with the release-provided `configure` script.
- Packaged programs: `udp-sender` and `udp-receiver`.
- Packaged data: two man pages and `include/udpcast/rateGovernor.h`.
- Conan dependencies: none.
- Platform libraries: libc, pthread, and libdl.
- Build tools: Perl and m4 for upstream man-page generation.

## OpenHarmony adaptation

The release's GNU configuration scripts do not recognize HarmonyOS. Two
portability patches add `HarmonyOS` detection and accept both
`aarch64-unknown-linux-ohos` and `aarch64-ohos-linux` input tuples.

The generated `configure` script also uses `umask 077` for the
`config.status` temporary directory. On HMDFS this produces a directory that
the mapped build user cannot write. A focused patch changes only the two
`confXXXXXX` creation paths to `umask 022`.

OpenHarmony does not provide `pthread_cancel`. The return-channel thread now
uses a C11 atomic stop flag without an OpenHarmony-specific preprocessor
branch. Shutdown wakes a possible producer/consumer wait, and a bounded
`select` wait lets the receive helper observe the flag with acquire/release
ordering and exit the worker before `pthread_join`; the shared UDP socket
remains open.

The upstream install target assumes an in-source build when copying
`rateGovernor.h`. The Conan recipe uses an out-of-source build, so packaging
copies the generated programs and man pages from the build folder and the
public header from the source folder explicitly.

Conan defines `CFLAGS`, so the default assignment in `configure.ac` is not
used. The recipe explicitly adds `-DBB_FEATURE_UDPCAST_FEC` to preserve the
upstream forward-error-correction feature on OpenHarmony.

## Tests

The default upstream build has no automated check target. The optional
`fec-test` target is not part of `all` and contains unguarded x86 timing/MMX
assembly, so it is not reported as an OpenHarmony upstream test execution.

The Conan consumer test executes both packaged programs, checks deterministic
CLI error boundaries, confirms the FEC option is compiled in, and transfers a
generated file over the loopback interface before comparing every output byte.

### Device validation

The final frozen input was
`udpcast-w3-r11-input.tar.gz` (14,043 bytes, SHA-256
`97e46dddced72fa9a94950fbe04127ca40a400aff9f1ea4c5f6f439231348e98`).
It was executed on `10.62.148.108` only, under
`/storage/Users/currentUser/ohpc-w3/udpcast-r11-20260807-0105`.

A fresh isolated Conan home was created on the device. `conan graph info` and
`conan install` with `--build=never` completed for the OHOS/aarch64 profile;
the graph contained only `udpcast/20250223` and had `info_invalid=0`.

A fresh isolated `conan create` on the same OpenHarmony PC completed with:

- recipe revision: `8c061d7b3ff4e076d79bf15680faf366`;
- package ID: `6b129b068851896169fae42d399fa922d239ce8a`;
- package revision: `0683f464bc4312d5463484ad29af356b`;
- build log: 20,206 bytes, SHA-256
  `6829aa7d43d4a5f09272c587409b545e738b2958e05f9ecfb0fe97f0f1933613`.

The package contains two executable programs, two man pages, the public
`rateGovernor.h` header, and `COPYING`. Both programs are AArch64 ELF64 PIE
executables using `/lib/ld-musl-aarch64.so.1`; each has only `libc.so` in
`DT_NEEDED`, `BIND_NOW`, `GNU_RELRO`, and a non-executable GNU stack. The
consumer test ended with `UDPcast command and loopback transfer tests passed`
and `CONAN_CREATE_RC=0`; its 64 KiB loopback payload was byte-identical. No
packaged executable contains a `pthread_cancel` symbol reference.

## Knowledge reuse

The configuration-script changes reuse E007 for HarmonyOS Autotools platform
detection and `openharmony-pc-autotools-patchng-hmdfs` for the `config.status`
temporary-directory permissions. The cooperative replacement for
`pthread_cancel` is recorded as
`openharmony-pc-pthread-cancel-cooperative-stop` in the local knowledge base.
