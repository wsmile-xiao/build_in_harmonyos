# FastNetMon 1.2.9 adaptation notes

## Scope

This first OHOS adaptation builds the `fastnetmon` daemon and keeps the core
NetFlow, sFlow, example collector, mitigation, Patricia trie, and traffic logic
targets. The package intentionally disables the following optional stacks:

- GoBGP/gRPC/protobuf API client
- Cap'n Proto serialization
- MongoDB reporting
- libpcap mirror capture
- AF_PACKET and AF_XDP Linux packet capture backends
- curses-based `fastnetmon_client`
- plugin runner and pcap reader

## Knowledge-Base Extension

This single-library adaptation is submitted as Path B (knowledge-base
extension). It records how to make a first OpenHarmony build of a network
daemon while preserving its core NetFlow, sFlow, collector, and traffic logic:
Linux-only packet-capture backends and their optional dependency closure are
explicitly disabled instead of being silently assumed available. The related
knowledge entry is `DRAFT-fastnetmon-packet-capture-gating.kv`.

The upstream default build probes Linux headers such as `linux/if_packet.h`,
`linux/if_xdp.h`, and `linux/bpf.h`, then pulls libbpf/libelf, libpcap,
gRPC/protobuf, Cap'n Proto, MongoDB, OpenSSL, log4cpp, ncurses, and compiled
Boost libraries. The package uses `boost/1.90.0.4`, the compiled-component
Boost package that provides the complete header set and libraries needed by
FastNetMon.

## Validation

The recipe builds and runs all five deterministic upstream `BUILD_TESTS`
executables before packaging, then the `test_package` runs `fastnetmon --help`
against the installed daemon. The two `ENABLE_FUZZ_TEST` wrappers require the
`afl-c++` compiler and are therefore disabled in the released package by
default. For local validation, set
`user.fastnetmon:enable_fuzz_validation=True` with AFL++ compiler wrappers;
the recipe then runs a fixed 15-second campaign for each harness and requires
nonzero AFL executions and zero saved crashes. The finite campaigns prove
harness execution and no observed crash for the seed/mutation window; they do
not claim a coverage percentage.

The release's `serialize_attack_description.blank_attack` expectation is stale:
it expects six `average_*` text fields that are absent from both the current
counter type and serializer, while the serializer emits the supported
`dropped_*` fields. The recipe synchronizes only that expected string to the
release implementation so the upstream test continues to validate its actual
serialization contract.

`traffic_structures_tests_real_traffic` hard-codes an unavailable developer
path for a 200,000-entry cable-ISP list. The recipe replaces that path with a
tracked 12-line IPv4 fixture containing unique and repeated addresses, then
runs the unmodified executable from the source directory. This validates the
parser and container benchmark path reproducibly; its throughput is not
reported as the upstream full-dataset benchmark.

The related `traffic_structures_tests` helper declares its callback as
`std::function<void(T&)>`, which prevents Clang from deducing a function
pointer argument. The recipe changes only the helper signature to a generic
callable template; this preserves every invocation while making the upstream
test compile under the Clang family used by OHOS and AFL++.

`speed_counters_performance_test` also hard-codes an unavailable developer
binary archive. The recipe creates a two-entry archive at the test's expected
source-relative location before exercising the original Boost binary archive
readback path. Upstream then runs its shard recalculation benchmark in an
infinite loop, which cannot be a CI test; the recipe bounds that exact loop to
three iterations while retaining the original load, sharding, thread creation,
recalculation, and timing paths. This proves serialization compatibility and
execution of the test target, but does not represent the upstream large-map
performance input.

`patricia_performance_tests` likewise expects untracked ISP prefix and traffic
files in the original developer's home directory. It now reads tracked CIDR
and JSON-lines fixtures, preserving its prefix parsing, JSON parsing, 1,000
round source/destination lookup loop, and timing calculation. The resulting
numbers are validation evidence only, not the original ISP-scale benchmark.

The AFL++ wrappers are not self-contained upstream executables: they omit the
unified packet parser library and duplicate an outdated subset of globals from
the daemon. The recipe adds the parser/runtime link closure and compiles
`fastnetmon.cpp` into a fuzz-only runtime library with its `main` excluded; the
harnesses then use the current daemon globals without starting the production
daemon or enabling capture/BGP actions. The runtime is linked with
`--whole-archive` because its global definitions otherwise have no direct
symbol reference from the harness entry points.

The daemon initializes its Patricia lookup trees during normal startup, but
the upstream fuzz wrappers jump directly into packet processing. The recipe
declares the runtime globals and creates empty IPv4/IPv6 trees before entering
the persistent AFL loops. This prevents the reproduced null-tree SIGSEGV in
`patricia_search_best2` while keeping capture, BGP, and traffic-monitoring
startup disabled.

The CMake reductions are applied in `conanfile.py` with deterministic
`replace_in_file()` calls because the upstream source uses LF line endings and
adding a standalone patch file introduced patch-file whitespace noise in local
`git diff --check`.
