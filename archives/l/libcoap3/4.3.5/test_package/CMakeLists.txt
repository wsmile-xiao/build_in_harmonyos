cmake_minimum_required(VERSION 3.15)
project(test_libcoap3 C)

# Find the package via Conan-generated CMakeDeps.
# The recipe exports cmake_file_name "libcoap" and target libcoap::coap-3
# (matching upstream's installed libcoapConfig.cmake).
find_package(libcoap REQUIRED)

add_executable(test_libcoap3 test.c)
target_link_libraries(test_libcoap3 libcoap::coap-3)

enable_testing()
add_test(NAME test_libcoap3 COMMAND test_libcoap3)
