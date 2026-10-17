# v4l 1.32.0 OpenHarmony adaptation record

## Basic information

- Software: v4l
- Upstream: v4l-utils
- Version: 1.32.0
- Build system: Meson
- Target: Linux or OHOS with V4L2/media kernel userspace APIs

## Build guidance

The default Conan recipe uses a minimal library-focused configuration. It
disables optional utilities, Qt frontends, BPF decoders, DVB support, gconv,
JPEG conversion, tracer support, plugins, wrappers, and documentation.

## Known limits

`v4l-utils` depends on Linux V4L2/media headers and ioctl semantics. The local
Windows workspace can validate recipe syntax and Conan export only. Full build
and runtime validation need OHOS/Linux. Device-level tests need `/dev/video*`,
`/dev/media*`, or related nodes.

## Verification

Local verification performed:

- `python -m py_compile conanfile.py test_package/conanfile.py`
- `conan inspect .`
- `conan export .`
- `git diff --check -- archives/v/v4l`
