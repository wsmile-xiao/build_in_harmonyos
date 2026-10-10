# SndObj 2.6.7 target test report

Date: 2026-10-04. Device: HarmonyOS PC arm64, `10.62.201.39:2222` at test time.

| Test set | Declared | Passed | Failed |
| --- | ---: | ---: | ---: |
| Noninteractive upstream registered tests | 0 | 0 | 0 |
| Installed Conan consumer conditions | 3 | 3 | 0 |

The consumer links the installed `sndobj` package, constructs a harmonic table, processes an oscillator vector, and checks finite, nonzero samples. Target `conan create` returned 0 and packaged `libsndobj.so`. The frozen W3 run `sndobj-w3-20261003T174232Z` verified a single launch, exact-byte transfer/readback, all 12 receipts, and no remaining task child process. Its `conan-create.log` SHA-256 is `bd48ebace8e9646f99baf3e7f4d3716090a409cd047992d8ec00b42c314f85d9`.

The release has no automated test target in `SConstruct`. The files named `src/examples/test.cpp` and `python/test.py` drive realtime audio; they require hardware and the optional realtime/wrapper configurations, so they were inventoried but not claimed as automated core tests. This package deliberately sets `NO_RTIO`; audio-device integration is unverified.
