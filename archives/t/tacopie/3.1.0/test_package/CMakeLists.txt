cmake_minimum_required(VERSION 3.15)
project(test_tacopie CXX)

# Find the package via Conan-generated CMakeDeps
find_package(tacopie REQUIRED)

# Consumer verification test (real TCP round-trip using the public API:
# tcp_server + tcp_client connect / async_read / async_write).
add_executable(test_tacopie test_tacopie.cpp)
target_link_libraries(test_tacopie tacopie::tacopie)

# HarmonyOS-specific verification test (loopback + echo on OHOS socket).
add_executable(test_tacopie_hmos test_tacopie_hmos.cpp)
target_link_libraries(test_tacopie_hmos tacopie::tacopie)

enable_testing()
add_test(NAME test_tacopie COMMAND test_tacopie)
add_test(NAME test_tacopie_hmos COMMAND test_tacopie_hmos)