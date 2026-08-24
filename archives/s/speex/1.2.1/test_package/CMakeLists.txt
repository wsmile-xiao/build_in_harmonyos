cmake_minimum_required(VERSION 3.15)
project(test_speex C)

# Find the package via Conan-generated CMakeDeps
find_package(speex REQUIRED)

add_executable(test_speex test.c)
target_link_libraries(test_speex speex::speex)

enable_testing()
add_test(NAME test_speex COMMAND test_speex)
