cmake_minimum_required(VERSION 3.15)
project(test_libfishsound C)

# Find the package via Conan-generated CMakeDeps
find_package(libfishsound REQUIRED)

add_executable(test_libfishsound test_libfishsound.c)
target_link_libraries(test_libfishsound libfishsound::libfishsound)

enable_testing()
add_test(NAME test_libfishsound COMMAND test_libfishsound)
