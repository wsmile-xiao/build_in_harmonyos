# SndObj 2.6.7 adaptation notes

- Target: HarmonyOS PC arm64, clang 15, Conan 2; result `built`, not `published`.
- Upstream source tarball SHA-256: `3707d05abf87ec129442b877b380cdda75b6e9dcf4f5baff443afb03229edba0`.
- Upstream `SConstruct` uses Python 2 constructs. The recipe's CMake overlay builds the portable `src/*.cpp` implementation plus bundled `src/rfftw/*.c`, excluding the unselected `FFT_alt.cpp`, `IFFT_alt.cpp`, and `SndASIO.cpp` variants. `NO_RTIO` excludes realtime backends.
- `src/SndWaveX.h` declared the non-Windows GUID fields as signed `int/short`, making subtype value `0x8312b9c2` ill-formed in C++ aggregate initialization. The single source patch changes them to unsigned types of the same widths.
- First target run `sndobj-w3-20261003T173429Z` packaged the library but failed while compiling our consumer, which incorrectly called `HarmTable::GetError()`. It was released as FAIL; no test result was reused.
- Corrected consumer uses `Table::GetLen()` and `Lookup()`. Local installed-library test passed, then new target run `sndobj-w3-20261003T174232Z` passed Conan create and 3/3 consumer assertions with 12/12 transaction receipts.
- `SConstruct` registers no noninteractive upstream test target. `src/examples/test.cpp` and `python/test.py` use realtime audio devices and are outside this `NO_RTIO` package scope; they are not counted as passed tests.
- No external host library dependency is required for this core configuration; W0 checked candidate FFTW/ALSA/JACK recipes but the final dependency graph is empty.
