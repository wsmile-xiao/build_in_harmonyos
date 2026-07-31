# xtrans

xtrans supplies the common X.Org network transport implementation used by
libX11, libICE, X servers, font servers, and related consumers. It is not a
shared library: each consumer includes `X11/Xtrans/transport.c` and compiles a
private implementation selected by namespace, role, and transport macros.

## Conan package

- Installs the seven upstream implementation files under `include/X11/Xtrans`.
- Installs a relocatable `share/pkgconfig/xtrans.pc` and `share/aclocal/xtrans.m4`.
- Depends on `xorgproto/2025.1` for `X11/Xfuncproto.h`, `X11/Xos.h`, and
  `X11/Xmd.h`.
- Uses the compiler declared by the Conan profile to detect whether target libc
  exports `fchown`, matching upstream `AC_CHECK_FUNC` behavior.
- Compiles one target capability preflight and 68 compile/link consumer
  configurations across six self-contained namespaces, four role profiles,
  and TCPv4, TCPv6, and UNIX transports. Their conditional references cover
  all 32 non-Windows public functions; these 69 build preflights are not
  executed or counted as tests.
- Runs full TCPv4 and TCPv6 loopback transactions, one OHOS UNIX-domain
  capability workflow, and one package-metadata workflow, for 4 independent
  substantive test cases in total. Runtime flows use bounded readiness waits
  and verify scalar/vector I/O, peer metadata, disconnect, and cleanup results.
- Submits the E234 knowledge draft with this software, generalizing the
  macro-matrix plus target-runtime testing pattern for source-distributed
  transport implementations without modifying the formal knowledge index.

Dependency Issue: #1291. The points task list has no xtrans entry, so this is a
dependency-only adaptation.
