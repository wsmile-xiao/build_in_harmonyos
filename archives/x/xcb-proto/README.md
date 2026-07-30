# xcb-proto

xcb-proto provides the XML descriptions and language-independent Python
generator helpers used to generate XCB protocol bindings.

## HarmonyOS adaptation

Version 1.17.0 is packaged as architecture-independent build data:

- 32 protocol XML documents and the upstream `xcb.xsd` schema;
- seven `xcbgen` Python modules under `lib/python3/site-packages`;
- a relocatable `xcb-proto.pc` exposing `xcbincludedir` and `pythondir`;
- the upstream XML-XCB format documentation and license.

The recipe runs the upstream schema command when `xmllint` can execute. Its
Conan test package runs 55 independent workflows: 32 protocol generator
register/resolve processes, 22 distinct public `xcbgen` API fixtures, and one
installed-package discovery workflow.

The adaptation uses Path A and Path B. Draft knowledge
`E240-draft-XCBP`, submitted beside this software, records the reusable test
design for protocol-data and generator packages.

## Dependency role

xcb-proto 1.17.0 is a build/data prerequisite of libxcb 1.17.0 and therefore
part of the X11/AWT dependency closure for OpenJ9 Issue #1084 and GraalVM
Issue #1085. It exports no linked library or runtime third-party dependency.

## References

- https://gitlab.freedesktop.org/xorg/proto/xcbproto
- https://xorg.freedesktop.org/archive/individual/proto/
