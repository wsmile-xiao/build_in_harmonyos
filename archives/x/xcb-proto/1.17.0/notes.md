# xcb-proto 1.17.0 adaptation notes

## Scope

- Dependency Issue: #1310.
- Downstream chain: xcb-proto -> libxcb -> libX11 -> OpenJ9 #1084 and
  GraalVM #1085 X11/AWT support.
- Path: A (basic adaptation) + B (reusable test knowledge).
- xcb-proto is outside the current contest task list, so it has one dependency
  Issue and no contest-claim Issue.

## Source and package design

The official X.Org archive matches SHA256
`2c1bacd2110f4799f74de6ebb714b94cf6f80fb112316b1219480fd22562148c`.
Upstream installs 32 protocol XML documents, `xcb.xsd`, and seven Python
modules. It also generates `xcb-proto.pc`, whose two consumer-facing variables
are `xcbincludedir` and `pythondir`.

This is a build/data package, not a C library. The Conan recipe therefore
copies the version-locked upstream inventories without running Autotools,
places Python source in a stable `lib/python3/site-packages/xcbgen` directory,
and exports that directory through both build and run `PYTHONPATH`. The
pkg-config file uses `${pcfiledir}/../..` as its prefix so both published paths
remain relocatable inside a Conan cache. The package has no libraries, binary
directories, or target-dependent output, so its package ID is cleared.

## Tests

Upstream defines one `check-local` command. The fresh HarmonyOS run found an
executable `xmllint` in the configured build environment and validated all 32
XML inputs against `xcb.xsd`. The recipe keeps upstream's explicit behavior:
if the tool cannot be found or started, this one upstream entry is a SKIP;
schema validation failures still fail the build.

The installed-package suite adds 55 independent workflows:

1. Thirty-two separate Python processes each load a different installed XML
   document through `xcbgen.state.Module`, register imports, resolve all
   protocol objects, and verify the namespace and base type table.
2. Twenty-two separate Python processes cover different public generator
   semantics with unique fixtures: alignment operations, field diagnostics,
   seven expression forms, core/extension namespaces, primitive/enum/padding
   and documentation types, output callback order, and missing-type failure.
3. One metadata workflow checks the exact XML and Python inventories, XSD,
   relocatable pkg-config variables, and that `xcbgen` resolves from the
   packaged `PYTHONPATH` rather than a system copy.

These are 55 entry processes with distinct inputs and failure boundaries. The
upstream schema suite is reported separately and is not counted again as 32
adapted tests. Shared/static variants do not exist for this data package, and
individual assertions are not split into extra cases.

Because every entry owns its input and process state, a command failure does
not invalidate later entries. The test recipe therefore records only
`ConanException` command failures, continues across the complete matrix, and
raises one aggregate exception after the metadata entry. Recipe or programming
exceptions outside `self.run()` are not caught. A local regression harness
injects two separated command failures plus an unrelated runtime exception to
lock both behaviors without increasing the reported test count.

This reuses the existing `E239-draft-I1R1` aggregation pattern from iir1 PR
#3000. The branch does not copy or submit another E239 draft; its own path B
contribution remains the distinct E240 protocol-data testing pattern.

The fresh target `conan create` passed all 55 workflows and packaged 32 XML,
one XSD, seven Python modules, one pkg-config file, one license, and one format
document. Raw log SHA256:
`4673326dbdf61031dc61364457f1d261eb232e0d1eaae193977fbe51fc594448`.

## Knowledge decision

Current `origin/main` contains no equivalent entry for testing protocol-data
packages at both the per-document generator boundary and installed discovery
boundary. `E240-draft-XCBP` records this reusable pattern. It remains a
`draft: true` KV/Markdown pair beside this software; this branch does not edit
the formal graph index, formal documentation, or `SUMMARY.md`.

## Dependencies

xcb-proto has no third-party Conan runtime, build, or tool requirement. Python
and optional xmllint are build/test environment tools. pkgconf is consumed by
downstream projects when they read `xcb-proto.pc`; it is not linked or exported
as a runtime dependency of this package.
---

**编译结束**: 2026-07-20 08:39
**最终状态**: built
