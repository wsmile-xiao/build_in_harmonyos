# dcap

dcap is the dCache access protocol client library. It provides a POSIX-like
client API (`libdcap`), an `LD_PRELOAD` interposition library (`libpdcap`),
the `dccp` copy tool, and IO tunnel plugins (telnet, ssl).

## HarmonyOS adaptation

The Conan recipe supports HarmonyOS PC arm64 with clang. The upstream GitHub
tag archive ships no generated `configure`, so the recipe bootstraps it with
`autoreconf -fi` (via `tool_requires` on automake/autoconf/libtool), passes an
explicit `--build/--host` triplet because `config.guess` cannot identify
HarmonyOS, and works around the HMDFS temporary-directory permission behavior
(`umask 077` → `022` in the generated `configure`).

## Dependencies

- `zlib/1.3.1` — required by upstream `configure` (hard error if missing).
- `openssl/3.5.6` — enables the ssl tunnel plugin.
- `cunit/2.1-3` — test-only requirement for the upstream `make check` suite,
  not exposed to consumers.

GSSAPI/Kerberos tunnel plugins are auto-disabled (no matching packages in the
registry); the core library, URL parsing, and `dcap://` transfers are complete.

## References

- Upstream: https://github.com/dCache/dcap
- Homepage: https://www.dcache.org

## Versions

| Version | Status | Date       |
|---------|--------|------------|
| 2.47.14 | built  | 2026-09-10 |
