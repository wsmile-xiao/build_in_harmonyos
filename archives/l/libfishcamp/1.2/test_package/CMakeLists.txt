cmake_minimum_required(VERSION 3.16)
project(test_package C)

find_package(fishcamp CONFIG REQUIRED)
# fishcamp's public header (fishcamp_common.h) includes <libusb.h>, so the test
# needs libusb's headers and link too.
find_package(libusb-1.0 CONFIG REQUIRED)

add_executable(test_fishcamp src/test_fishcamp.c)
target_link_libraries(test_fishcamp PRIVATE fishcamp::fishcamp libusb-1.0::libusb-1.0)

enable_testing()
add_test(NAME test_fishcamp COMMAND test_fishcamp)
