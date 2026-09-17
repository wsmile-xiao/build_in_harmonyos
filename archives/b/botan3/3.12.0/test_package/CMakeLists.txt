cmake_minimum_required(VERSION 3.15)
project(test_botan3 CXX)

# Botan 3 public headers require C++20; the shared ohos-aarch64 profile
# defaults to cppstd=17, so the requirement is declared at target level.
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(botan3 REQUIRED CONFIG)

add_executable(test_botan3 test_botan3.cpp)
target_compile_features(test_botan3 PRIVATE cxx_std_20)
target_link_libraries(test_botan3 PRIVATE botan3::botan3)

add_executable(test_botan3_gcm test_botan3_gcm.cpp)
target_compile_features(test_botan3_gcm PRIVATE cxx_std_20)
target_link_libraries(test_botan3_gcm PRIVATE botan3::botan3)

enable_testing()
add_test(NAME botan3_sha256 COMMAND test_botan3)
add_test(NAME botan3_aes_gcm COMMAND test_botan3_gcm)
