cmake_minimum_required(VERSION 3.12)
project(test_libebur128 C CXX)

find_package(libebur128 REQUIRED CONFIG)

# 1) Consumer assertion suite (11 checks against the installed package).
add_executable(test_libebur128 test_libebur128.c)
target_link_libraries(test_libebur128 libebur128::libebur128)

# 2) Upstream test programs, verbatim (see upstream/README.md).
#    tests.c / minimal-example.c use libsndfile only to read RIFF PCM
#    wav files; the shim in sndfile_stub/ implements that exact surface.
add_executable(r128-test-library upstream/tests.c sndfile_stub/sndfile_stub.c)
target_include_directories(r128-test-library PRIVATE sndfile_stub)
target_link_libraries(r128-test-library libebur128::libebur128 m)

add_executable(minimal-example upstream/minimal-example.c sndfile_stub/sndfile_stub.c)
target_include_directories(minimal-example PRIVATE sndfile_stub)
target_link_libraries(minimal-example libebur128::libebur128 m)

#    fuzzer.cpp is self-contained (no sndfile); driven by fuzzer_driver.cpp
#    with deterministic pseudo-random inputs (no libFuzzer on OHOS clang).
#    The malloc/calloc macros replace the fault-injecting wrappers inside
#    the upstream fuzzer translation unit ONLY — the driver must keep the
#    real malloc or injected failures abort it silently.
add_executable(r128-fuzzer upstream/fuzzer.cpp fuzzer_driver.cpp)
set_source_files_properties(upstream/fuzzer.cpp PROPERTIES
    COMPILE_DEFINITIONS "malloc=my_malloc;calloc=my_calloc")
target_link_libraries(r128-fuzzer libebur128::libebur128 m)
