cmake_minimum_required(VERSION 3.15)
project(test_littlefs C)

# Find the package via Conan-generated CMakeDeps
find_package(littlefs REQUIRED)

add_executable(test_littlefs harmonyos_test.c)
target_link_libraries(test_littlefs PRIVATE littlefs::littlefs)

enable_testing()
add_test(NAME test_littlefs COMMAND test_littlefs)
