# E321 - Make optional acceleration backends explicit in static packages

> **Contributor**: RH46 | **Status**: DRAFT | **Created**: 2026-08-21

## Symptom

A configure-based project builds a static package successfully on one worker,
but another worker or a downstream consumer fails with `OpenSSL library not
found`, `cannot find -lcrypto`, or unresolved crypto symbols. The configure
summary may show that OpenSSL was enabled only because it happened to be
installed on the build worker.

## Root cause

Configure-time autodetection is outside the Conan dependency graph. When an
optional library is discovered from the worker, its headers and link flags can
leak into the package without a declared requirement. Static consumers must
then supply that undeclared library, and the package result varies by worker.

Disabling such a backend is correct only after checking the upstream contract.
Some backends provide required protocols or algorithms; others only accelerate
implementations that upstream already ships internally.

## Decision rule

1. Determine whether the backend changes public functionality or only
   performance.
2. If it is required functionality, declare a Conan requirement and enable the
   backend explicitly.
3. If it is acceleration-only and the package contract is a self-contained
   static library, disable it explicitly and document that decision.
4. Run the complete upstream suite and an installed consumer test to prove the
   internal implementation still covers the public API.
5. Do not leave the configure result to worker autodetection.

## RHash 1.4.6 evidence

RHash describes `--enable-openssl` as support for "optimized hash functions".
It ships internal implementations of the supported digest algorithms, so
`--disable-openssl` does not remove an algorithm or a TLS/security protocol.
The HarmonyOS recipe deliberately builds a dependency-free static
`librhash.a` and CLI, rather than linking an OpenSSL installation detected from
the worker.

Validation on HarmonyOS aarch64 covered:

- all 25 upstream CLI tests via `make -j1 test`;
- the upstream static library algorithm suite via `make -j1 test-lib`;
- a Conan consumer checking MD5 and SHA1 through the public C API;
- shadow CI plus PR CI builds #28842 and #28931.

## Boundary

This pattern must not be used to remove required functionality. If a package
needs OpenSSL for TLS, certificate handling, a public algorithm, or another
advertised feature, model OpenSSL as a Conan dependency and test that feature
instead of disabling it.

## Related knowledge

No equivalent formal entry was present when this RHash draft was created. The
draft is limited to explicit policy for optional acceleration dependencies in
reproducible static packages.
