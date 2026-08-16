# nanopb 0.4.9.1 HarmonyOS adaptation notes

## Package scope

nanopb provides a small ANSI C Protocol Buffers runtime plus an optional Python/protoc based code generator. This recipe packages the C runtime library and headers.

The generator is disabled by default because it introduces host tooling requirements (`protoc`, Python protobuf modules) that are separate from the target C runtime.

## Patch list

| Patch | Purpose |
| --- | --- |
| `0001-cmake-runtime-without-generator-deps.patch` | Guard `protoc` and Python discovery behind `nanopb_BUILD_GENERATOR`, allowing runtime-only C library builds on HarmonyOS without generator dependencies. |

## HarmonyOS validation

- `conan create archives/n/nanopb/0.4.9.1 --profile=ohos-aarch64 --build=missing`
- `test_package` builds a C consumer and verifies protobuf wire encode/decode using `pb_encode_tag`, `pb_encode_varint`, `pb_encode_string`, `pb_decode_tag`, `pb_decode_varint`, and `pb_read`.

Result: passed on HarmonyOS aarch64. `test_package` reports `nanopb_wire_roundtrip` passed.

## Upstream tests

The upstream suite is SCons based and exercises both generated code and the Python/protoc generator path. This recipe packages the C runtime with `nanopb_BUILD_GENERATOR=OFF`; therefore the generator/protoc SCons suite is not used as the runtime-only package gate.
