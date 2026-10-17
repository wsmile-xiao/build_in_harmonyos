cmake_minimum_required(VERSION 3.15)
project(test_atomix C)

# Find the package via Conan-generated CMakeDeps
find_package(atomix REQUIRED)

add_executable(test_atomix test.c)
target_link_libraries(test_atomix atomix::atomix)

enable_testing()
add_test(NAME test_atomix COMMAND test_atomix)
