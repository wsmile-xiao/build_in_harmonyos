cmake_minimum_required(VERSION 3.15)
project(usbmuxd_consumer_test C)

# Find libusbmuxd via Conan-generated CMakeDeps (libusbmuxd 2.0.2
# test_package precedent: find_package + libusbmuxd::libusbmuxd target)
find_package(libusbmuxd REQUIRED)

add_executable(usbmuxd_consumer_test test.c)
target_link_libraries(usbmuxd_consumer_test PRIVATE libusbmuxd::libusbmuxd)
