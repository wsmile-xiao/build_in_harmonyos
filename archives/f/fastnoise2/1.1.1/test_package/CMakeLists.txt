cmake_minimum_required(VERSION 3.15)
project(test_fastnoise2 C CXX)

# FastNoise2 C API is plain C; the C++ static library requires C++17 for the
# HarmonyOS special test (C++ API + FastSIMD feature detection).
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(fastnoise2 REQUIRED)

# Consumer test: plain-C consumer using only the public C API (FastNoise_C.h)
# libFastNoise.a contains C++ objects (std::string etc.) -> link via C++ driver
add_executable(test_fastnoise2 test.c)
target_link_libraries(test_fastnoise2 FastNoise2::FastNoise2)
target_compile_definitions(test_fastnoise2 PRIVATE FASTNOISE_STATIC_LIB)
set_target_properties(test_fastnoise2 PROPERTIES LINKER_LANGUAGE CXX)

# HarmonyOS special test: platform checks + determinism + C/C++ cross-consistency
add_executable(test_ohos_special ohos_special_test.cpp)
target_link_libraries(test_ohos_special FastNoise2::FastNoise2)
target_compile_definitions(test_ohos_special PRIVATE FASTNOISE_STATIC_LIB)

enable_testing()
add_test(NAME test_fastnoise2 COMMAND test_fastnoise2)
add_test(NAME test_ohos_special COMMAND test_ohos_special)