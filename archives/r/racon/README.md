# racon

Racon is an ultrafast consensus module for raw de novo DNA assembly of long
uncorrected reads (Oxford Nanopore / PacBio). It polishes contigs from
overlaps (MHAP/PAF/SAM) and can also correct reads from all-vs-all overlaps.

## OHOS adaptation

- CMake C++11 project; builds `libracon` plus the `racon` CLI.
- CUDA support and the Python wrapper are disabled on OHOS.
- Dependencies: `bioparser/3.0.15` via Conan, `edlib/1.2.7` vendored,
  `spoa exact 4.0.8` via upstream FetchContent;
  `thread_pool 4.0.0` and `GTest 1.10.0` via upstream FetchContent.
- Upstream tests: 15 gtest cases in `test/racon_test.cpp`, run via the
  `racon_test` binary (upstream has no ctest registration).
- Consumer tests call the real `racon::createSequence` / `PolisherType` API
  and smoke-test `racon --version`.

## Dependencies

- `bioparser/3.0.15` — FASTA/Q + MHAP/PAF/SAM parsing (exact version)
- `edlib/1.2.7` — edit-distance library (exact version)
- `spoa exact 4.0.8` — partial-order alignment via upstream FetchContent (registry 4.1.5 breaks exact assertions)

## References

- https://github.com/lbcb-sci/racon
- https://github.com/lbcb-sci/racon/releases/tag/1.5.0
