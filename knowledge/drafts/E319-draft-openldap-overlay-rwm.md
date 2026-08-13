# E319 - Validate Packaged Loadable Modules with a Private Host

## Problem

Some packages deliver a dynamically loaded module rather than a standalone
library or command. Such a module may have no public header or stable function
that a normal consumer program can compile and call.

A test that only checks whether the module file exists is insufficient. It
does not prove that:

- the runtime loader can open the module;
- all transitive shared-library dependencies resolve;
- the module ABI matches its host;
- module initialization and registration succeed; or
- the host accepts module-specific configuration.

Using a host from the operating system is also unsafe because it can differ
from the packaged module in revision, build options, dependencies, or ABI.

## Applicable Packages

Use this pattern for plugins, overlays, providers, backends, and similar
loadable components when all of the following are true:

- the module is the package's primary public artifact;
- no independent public API can exercise it directly;
- upstream provides a host-side validation, parse, or probe mode; and
- packaging the complete host product would add unrelated dependencies or
  commands.

## Recommended Pattern

1. Build the module and the smallest supported host from the same source tree
   and dependency graph so their ABI and feature selections match.
2. Package the host and required configuration data in private directories.
   Do not advertise the validation-only host through public `bindirs`.
3. Resolve every module, schema, and data path from the Conan package folder.
   Do not depend on a system installation or a fixed cache path.
4. Generate the smallest configuration that loads the module and invokes at
   least one module-specific directive.
5. Run the host's non-destructive validation mode and require a zero exit
   status.
6. Relocate or remove the package artifact directories and run the consumer
   test again. The sabotaged test must fail, after which the artifacts must be
   restored.
7. Treat this focused consumer check as complementary to upstream integration
   tests. If upstream coverage needs components outside the package scope,
   build the smallest same-source fixtures for the test phase, run the selected
   upstream entries, and remove the fixture artifacts before packaging.
8. Probe temporary storage for the operations the upstream harness actually
   needs, such as writable files and FIFOs. Select a private test directory by
   capability instead of assuming that a writable path supports Unix service
   primitives.

The positive check proves the module can be loaded and configured. The
destructive check proves the test actually depends on packaged artifacts.

## OpenLDAP RWM Evidence

`openldap-overlay-rwm/2.6.13` applies this pattern as follows:

| Role | Packaged artifact |
|------|-------------------|
| Public module | `libexec/openldap/rwm.so` |
| Private ABI-matched host | `libexec/slapd` |
| Required configuration data | `etc/openldap/schema/core.schema` |
| Module-specific configuration | `overlay rwm` and `rwm-suffixmassage` |

The Conan `test_package` generates an absolute-path configuration and runs:

```sh
<package>/libexec/slapd -Tt -f <build>/slapd-rwm.conf
```

This exercises libltdl loading, OpenLDAP module initialization, overlay
registration, schema parsing, and rwm-specific configuration without starting
a network listener. Shadow CI and AtomGit PR CI both passed this check. The CI
L1e destructive run then moved package artifact directories away and confirmed
that the same consumer test failed.

The focused package test is paired with eight upstream rwm integration and
regression entries. `back_ldap`, `back_relay`, and `syncprov` are built as
same-source test fixtures, the original upstream assertions run against the
newly built target programs, and those three fixture modules are removed before
packaging. The final package module directory therefore contains only `rwm.so`
and its versioned links.

OpenLDAP's daemon harness requires named pipes. A path may pass ordinary
create/write/remove checks but still reject `mkfifo`, as HMDFS-backed user
storage does on HarmonyOS. The recipe creates an isolated candidate directory,
probes both file I/O and FIFO creation, and uses it only after both succeed.
On the verified target, `/data/storage/el2/base/cache` provided the required
capabilities. Test scripts and generated helpers are invoked through
`CONFIG_SHELL`, and `umask 007` keeps their shared-device directories usable
without weakening them to world access.

Fresh-build Shadow CI runner
`codex-openldap-overlay-rwm-issue-2044-r16i-final-upstream-tests-20260812-190906-919`
executed and passed all eight upstream entries, then passed the private-host
`test_package`. The resulting upstream pass rate was 100% (8/8).

## Forbidden Shortcuts

- Do not accept `exists(rwm.so)` or an equivalent file-presence assertion as
  runtime validation.
- Do not load the package module into an unrelated system host.
- Do not hard-code a Conan cache, device home, schema, or module path.
- Do not expose the private validation host as a supported package command.
- Do not claim upstream integration tests passed when only the focused package
  validation ran.
- Do not ship test-only backends or helper modules merely because upstream
  integration tests need them during the build.
- Do not select service-test storage from writability alone when the harness
  also needs FIFOs, sockets, locks, or other filesystem capabilities.

## Verification Checklist

| Check | Expected result |
|-------|-----------------|
| Module and private host provenance | Same source revision and build graph |
| Generated paths | Resolve inside the tested Conan package |
| Validation-only host run | Exit status 0 |
| Module-specific directive | Parsed and accepted |
| Missing-artifact run | Nonzero exit status |
| Public command surface | Private host is not advertised in `bindirs` |
| Same-source upstream fixtures | Built for tests, absent from final package |
| Upstream entries | Real target execution with terminal success markers |
| Temporary storage | File-I/O and FIFO probes both pass |

## Scope Boundary

The private-host pattern verifies packaging, loading, initialization, and
configuration. It does not replace the upstream project's network, protocol,
or multi-backend integration coverage. Runnable upstream entries must be
executed and counted separately; any build-only fixtures must remain outside
the final package contract.

## Source

- Package: `openldap-overlay-rwm/2.6.13`
- Issue: `#2044`
- Pull request: `#5121`
- Verified on: aarch64 HarmonyOS PC Shadow CI and AtomGit PR CI
