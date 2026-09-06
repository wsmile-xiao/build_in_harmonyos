# Source audit

## Provenance

| Field | Value |
|---|---|
| Upstream repository | https://github.com/pantor/ruckig |
| Release tag | `v0.19.4` |
| Commit | `a8db97a4e9c55e5160a3855f739fa3b270df8e4c` |
| Published | 2026-07-15T07:07:01Z |
| Archive | https://github.com/pantor/ruckig/archive/refs/tags/v0.19.4.tar.gz |
| Size | 882534 bytes |
| SHA256 | `4f57caa350770ce162aed92285fc07ac23e83b89bf802f5f500fb4bc8b2a1905` |
| License | MIT |

The clean archive URL and the URL used by `init-build` produced byte-identical
files and the same SHA256.

## Build inputs

The top-level CMake project declares `LANGUAGES CXX` and requires C++20 for the
`ruckig` target. It links no mandatory external libraries. The optional Python
module uses nanobind and the optional Rust wrapper uses cxx, but neither wrapper
is part of this Conan C++ package. The optional cloud client uses vendored
cpp-httplib and nlohmann/json and is disabled for the packaged local core.

## Tests

Upstream CI builds cloud-client ON and OFF configurations. On Linux it runs
`test-target 5000000`, while all three host operating systems run six local C++
examples. The doctest source defines 15 top-level test cases and six subcases.
The full workload reported 26,250,183 passing runtime assertions on Windows and
26,250,188 on HarmonyOS aarch64.
