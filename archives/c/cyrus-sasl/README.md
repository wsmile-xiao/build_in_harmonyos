# cyrus-sasl

## Introduction

Cyrus SASL provides the `libsasl2` authentication framework used by mail,
directory, database, and network services that negotiate SASL mechanisms.

This archive tracks the OpenHarmony PC adaptation of Cyrus SASL 2.1.28.
The current package recipe revision is `2.1.28.1`.

## Package Scope

Initial recipe scope:

- Core `libsasl2` library and public headers.
- Static mechanism support for the self-contained mechanisms kept by the first
  pass.
- Conan consumer test covering version query, client/server initialization, and
  mechanism list APIs.

Disabled in the initial recipe:

- `saslauthd`, `pwcheck`, and authdaemon integration.
- PAM, LDAP, SQL, Berkeley DB, Kerberos/GSSAPI, OPIE, DES, OpenSSL, and other
  platform/service-dependent authentication closures.
- Sample programs and upstream test execution.

## Difficulty Notes

- Full Cyrus SASL validation is protocol- and service-heavy: useful coverage
  normally spans client/server negotiation, password verifiers, plugin loading,
  auxprop backends, and external authentication services.
- The first package deliberately validates the reusable library surface while
  avoiding OHOS runtime plugin path and system-authentication dependencies.
