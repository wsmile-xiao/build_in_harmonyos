# libgkarrays

Gk-arrays index k-mers of large NGS read collections and answer count/location
queries from memory. This package builds the C++ library (`libGkArrays`) with
its bundled ProgressBar helper and exposes the `libGkArrays::libGkArrays`
CMake target plus `GkArrays` link library.

Upstream 2.1.0 `make check` runs three offline tests
(`testPairedEnd`, `testVariableFixed`, `testConsistency`) over the bundled
`tests/dataset/*.fa` fixtures. The consumer links the installed library and
checks version reporting, read filtering (`isDiscarded`) and `SolArray`
set/get behavior.

Upstream homepage (retired GForge): http://crac.gforge.inria.fr/gkarrays/
Source used: Debian/Ubuntu dfsg repack (authoritative archives, identical bytes).
