cmake_minimum_required(VERSION 3.15)
project(test_pcre2 C)

# Find the package via Conan-generated CMakeDeps
find_package(pcre2 REQUIRED)

add_executable(test_pcre2 test.c)
target_link_libraries(test_pcre2 pcre2::pcre2)

enable_testing()
add_test(NAME test_pcre2 COMMAND test_pcre2)
