cmake_minimum_required(VERSION 3.15)
project(test_gmime C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=gmime-3.0)
find_package(gmime-3.0 CONFIG REQUIRED)

add_executable(test_gmime test.c)
target_link_libraries(test_gmime gmime-3.0::gmime-3.0)

enable_testing()
add_test(NAME test_gmime COMMAND test_gmime)
