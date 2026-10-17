cmake_minimum_required(VERSION 3.15)
project(test_elfio CXX)

set(CMAKE_CXX_STANDARD 17)

# Find the package via Conan-generated CMakeDeps
find_package(elfio REQUIRED)

add_executable(test_elfio test_elfio.cpp)
target_link_libraries(test_elfio elfio::elfio)

enable_testing()
add_test(NAME test_elfio COMMAND test_elfio)

# HarmonyOS special test: parse a real OHOS aarch64 ELF + aarch64 round-trip
add_executable(test_harmonyos_elf test_harmonyos_elf.cpp)
target_link_libraries(test_harmonyos_elf elfio::elfio)
add_test(NAME test_harmonyos_elf COMMAND test_harmonyos_elf)
