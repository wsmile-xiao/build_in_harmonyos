# Boost 1.91.0.1 Graph dependency repair

## Scope

This recipe is the first adaptation-fix suffix for the official stable Boost
1.91.0 release. It keeps the verified official
`boost-1.91.0-1-cmake.tar.xz` source and adds the Boost.Graph component that
Redex v2026.04.30 actually requires through
`boost/pending/disjoint_sets.hpp`.

The published `boost/1.91.0` package has a valid include root, but it does not
contain that header because `graph` was absent from `BOOST_INCLUDE_LIBRARIES`.
The repair stays in the dependency package; Redex must not copy the header or
invent an imported target.

## Component contract

The official `boostorg/graph` `boost-1.91.0` CMake target is a compiled
`Boost::graph` library. Its public dependency closure includes header-only
Boost targets plus `Boost::random` and `Boost::serialization`; its private
dependency is the interface target `Boost::regex`. Selecting Graph also builds
and installs `boost_serialization` and `boost_wserialization`, so the Conan
metadata exports all three additional compiled artifacts and their target
relationships.

`Boost::graph` is represented by the Conan component `graph` with the official
CMake target name. The many public header-only upstream targets are collapsed
to the package's `headers` component, while `random`, `serialization`, and
`regex` remain explicit component requirements. Shared and static consumers
receive the same Graph and Serialization compile definitions as the official
CMake targets.

## Validation results

Upstream result: **17/17 PASS**. Consumer result: **6/6 PASS**. The selected
inventory is the 16 inherited unmodified upstream flows plus the one official
Boost.Graph leaf directly tied to the missing header:

- `boostorg/graph@boost-1.91.0:test/disjoint_set_test.cpp`
- official Git blob: `929de701087e906dd45160a2872420f1cf93d662`
- copied-file SHA-256:
  `6ee81b50d376bde845c5b6df4af03a8c3d5ea0c8b46d42b063fbd4123fd184b5`
- registration: `[ run disjoint_set_test.cpp ]` in the official
  `test/Jamfile.v2`

The copied upstream file is byte-identical to that tag and is a separate test
from `graph.cpp`. The latter is a consumer contract that both exercises
`disjoint_sets_with_storage` and calls the compiled `read_graphviz` API through
`Boost::graph`; it contributes eight consumer assertions, not another upstream
test. `boost/pending/disjoint_sets.hpp` must precede the broader Graph headers
so its pointer property-map `get()` calls are defined before Graph overloads
enter the lookup set.

The authorized HarmonyOS AArch64 r2 run built shared and static modes with one
job. Both variants executed the selected tests and produced exactly 12 real
libraries, no symlinks, the missing disjoint-set header, and the Graph and
Serialization CMake targets. The upstream total remains 17, not 34, because a
passed upstream test is counted once across package variants.

The first target attempt is retained as FAILED. Its consumer included broad
Graph headers before `disjoint_sets.hpp`, and its Windows snapshot exported
the CI scripts with CRLF. The r2 snapshot used
`git -c core.autocrlf=false archive`, rejected CR bytes before Conan, and
passed both the consumer compilation and standard `setup.sh`/W3 path.

The `finish`-generated W3 record has `exit_code=0` and integrity hash
`75157133beb5ee2a`. The outer legacy finish command returned 1 after W3 because
it still requires standalone packaging/staging artifacts for a Conan recipe
and its `SUMMARY.md` generator raised a framework-only error. No empty marker
or fabricated tar was added; the runner accepted W3 only after validating the
generated record, complete CI log, both package variants, and the closed
evidence manifest.

Validated package references:

- shared: `boost/1.91.0.1#ccc10888355643c45a0d36cc1d4d6252:01d92cf349a0dd98ff915f4bd99a04430171517f#0312dae59411525c45dd8a92b0989645`
- static: `boost/1.91.0.1#ccc10888355643c45a0d36cc1d4d6252:21b17f8b2bc0e9511e276e3d57a23893067cefe5#55c548ebbc62c19554bcfaa84eb3cce1`

## Tracking

- Downstream Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1092
- Dependency task: `boost/1.91.0.1`, activity `开源鸿蒙PC专项积分赛-依赖`
- Branch: `feat/boost-1.91.0.1`
