cmake_minimum_required(VERSION 3.15)
project(test_libimobiledevice C)

# Find the package via Conan-generated CMakeDeps
find_package(libimobiledevice REQUIRED)
find_package(libplist-2.0 REQUIRED)

add_executable(test_libimobiledevice test.c)
target_link_libraries(test_libimobiledevice libimobiledevice::libimobiledevice libplist::libplist)

enable_testing()
add_test(NAME test_libimobiledevice COMMAND test_libimobiledevice)
