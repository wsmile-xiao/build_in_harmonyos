cmake_minimum_required(VERSION 3.15)
project(test_cista CXX)

find_package(cista REQUIRED)

add_executable(test_cista test.cpp)
target_link_libraries(test_cista PRIVATE cista::cista)
target_compile_features(test_cista PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_cista COMMAND test_cista)

# HarmonyOS-specific verification executable (R04): real cista-API test that
# runs on the OHOS aarch64 verification path (host aarch64 userland).
add_executable(test_cista_hmos test_hmos.cpp)
target_link_libraries(test_cista_hmos PRIVATE cista::cista)
target_compile_features(test_cista_hmos PRIVATE cxx_std_17)
add_test(NAME test_cista_hmos COMMAND test_cista_hmos)