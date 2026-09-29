cmake_minimum_required(VERSION 3.15)
project(vosk-api-test C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_EXTENSIONS OFF)

# Both packages are provided by Conan's CMakeDeps generator.
find_package(vosk REQUIRED)
find_package(openfst REQUIRED)

# Consumer test: links the packaged libvosk.so and drives the public C API
# declared in <vosk_api.h>.
add_executable(test_vosk test_vosk.c)
target_link_libraries(test_vosk PRIVATE vosk::vosk)

# Test-only fixture generator: writes a byte-level identity transducer with
# OpenFst. Kept as a separate binary that does NOT link libvosk.so so that the
# two statically-linked OpenFst copies never coexist in one process.
add_executable(make_identity_fst make_identity_fst.cpp)
target_link_libraries(make_identity_fst PRIVATE openfst::openfst)

# HarmonyOS-specific probe: dlopen()s libvosk.so through the OHOS loader the
# same way the ctypes-based bindings do, then resolves the C API symbols.
add_executable(ohos_dlopen_probe ohos_dlopen_probe.c)
target_link_libraries(ohos_dlopen_probe PRIVATE ${CMAKE_DL_LIBS})
