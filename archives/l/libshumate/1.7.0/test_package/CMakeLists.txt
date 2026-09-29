cmake_minimum_required(VERSION 3.15)
project(test_libshumate C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=shumate-1.0).
find_package(shumate-1.0 CONFIG REQUIRED)

add_executable(test_libshumate test.c)
target_link_libraries(test_libshumate shumate-1.0::shumate-1.0)

enable_testing()
add_test(NAME test_libshumate COMMAND test_libshumate)
