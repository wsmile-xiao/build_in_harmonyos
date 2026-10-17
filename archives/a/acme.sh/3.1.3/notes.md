# acme.sh 3.1.3 adaptation notes

## Scope

- Package: `acme.sh/3.1.3`
- Issue: #590
- Source: `https://github.com/acmesh-official/acme.sh/archive/refs/tags/3.1.3.tar.gz`
- SHA256: `efd12b265252f8875269960b6b31830731ccce2b3e6ff8e7ecfbee21fde35ab4`

## Adaptation

- Packages the upstream shell client and its `dnsapi`, `deploy`, and `notify`
  helpers without compiling target binaries.
- Installs a relocatable wrapper that also works when invoked through `PATH`.
- Keeps all tests deterministic and independent of ACME credentials.

## Tests

The 3.1.3 release archive does not bundle the external `acmetest` integration
repository. Those issuance workflows require Pebble, network services, or DNS
provider credentials. The two self-contained gates from the upstream
`shellcheck.yml` workflow were reproduced locally:

- ShellCheck: passed over 254 shell scripts.
- shfmt: passed over 254 shell scripts.

The added `test_package` verifies the wrapper, `PATH` invocation, helper
directories, version output, and help output. It contains one deterministic
scenario with 11 assertions.

## Local validation

- Linux x86_64 `conan create`, Release: passed.
- Upstream self-contained quality gates: 2/2 passed.
- Added consumer test: 1/1 passed; 11/11 assertions passed.
- External credentialed issuance workflows are not counted as executed tests.
- The local Docker preflight is not an official OHOS armv8 CI result.
