cmake_minimum_required(VERSION 3.15)
project(test_nanoflann CXX)

find_package(nanoflann REQUIRED)

add_executable(test_nanoflann test.cpp)
target_link_libraries(test_nanoflann PRIVATE nanoflann::nanoflann)
target_compile_features(test_nanoflann PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_nanoflann COMMAND test_nanoflann)

# HarmonyOS-specific verification executable (R02): uses the packaged
# nanoflann header for a real kNN + radius + rank-kNN search, compiled for
# and run on the OHOS aarch64 verification path (host aarch64 userland).
add_executable(test_nanoflann_hmos test_hmos.cpp)
target_link_libraries(test_nanoflann_hmos PRIVATE nanoflann::nanoflann)
target_compile_features(test_nanoflann_hmos PRIVATE cxx_std_17)
add_test(NAME test_nanoflann_hmos COMMAND test_nanoflann_hmos)