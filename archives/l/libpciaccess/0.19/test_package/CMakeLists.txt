cmake_minimum_required(VERSION 3.15)
project(test_libpciaccess C)

# Find the package via Conan-generated CMakeDeps
find_package(libpciaccess REQUIRED)

add_executable(test_libpciaccess test.c)
target_link_libraries(test_libpciaccess libpciaccess::libpciaccess)

# HarmonyOS-specific consumer test: verifies the platform's restricted PCI
# access contract while calling the actual libpciaccess initialization API.
add_executable(test_libpciaccess_harmonyos harmonyos_platform.c)
target_link_libraries(test_libpciaccess_harmonyos libpciaccess::libpciaccess)

enable_testing()
add_test(NAME test_libpciaccess COMMAND test_libpciaccess)
add_test(NAME test_libpciaccess_harmonyos COMMAND test_libpciaccess_harmonyos)
