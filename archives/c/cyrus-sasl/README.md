# cyrus-sasl

## Introduction

Cyrus SASL provides the `libsasl2` authentication framework used by mail,
directory, database, and network services that negotiate SASL mechanisms.

This archive tracks the OpenHarmony PC adaptation of Cyrus SASL 2.1.28.
The current package recipe revision is `2.1.28.3`.

## Version history

| Version | Status | Scope |
|---------|--------|-------|
| `2.1.28.3` | built | Shared `libsasl2.so.3` + 4 dlopen'ed mechanism plugins (`db_none`, zero conan runtime dependencies). Verified locally with a real `conan create` (W3 gates green). |
| `2.1.28.1` | built | Earlier recipe revision of the same upstream source. |

## Package Scope

Current recipe scope (`2.1.28.3`):

- Shared `libsasl2.so.3` (SONAME `libsasl2.so.3`) and the public headers.
- Mechanism plugins under `lib/sasl2/`: `DIGEST-MD5`, `CRAM-MD5`, `PLAIN`,
  `ANONYMOUS` (plus the built-in `EXTERNAL`); the plugin directory is exposed
  through the Conan run environment (`SASL_PATH`).
- Zero conan runtime dependencies: `libsasl2.so.3` links only against system
  libraries (`DT_NEEDED` = `libc.so`).
- Conan consumer test covering version query, client initialisation,
  connection setup, mechanism enumeration and plugin loading.

Disabled in this recipe:

- `saslauthd`, `pwcheck`, and authdaemon integration.
- PAM, LDAP, SQL, Berkeley DB/GDBM, Kerberos/GSSAPI, OPIE, DES, OpenSSL, and
  other platform/service-dependent authentication closures.
- Sample programs.

The delivered package is a **pure library** (no executables), so it carries no
`commands.json` (R38).

## Difficulty Notes

- Full Cyrus SASL validation is protocol- and service-heavy: useful coverage
  normally spans client/server negotiation, password verifiers, plugin loading,
  auxprop backends, and external authentication services.
- The upstream release registers no automake test suite (`make check` is empty);
  the bundled `utils/testsuite` harness requires a real `sasldb` backend and is
  therefore not run by the `db_none` shipped configuration. See the version
  `notes.md` and `test_package/MANIFEST.yml` for the full inventory.
- The package validates the reusable library surface while avoiding OHOS
  runtime plugin-path and system-authentication dependencies.
