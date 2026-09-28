cmake_minimum_required(VERSION 3.15)
project(test_readstat C)

# Consumer view: locate the packaged library through the Conan-generated
# CMakeDeps config (readstat::readstat) and link the packaged artifact only.
find_package(readstat REQUIRED)

add_executable(test_readstat test.c)
target_link_libraries(test_readstat readstat::readstat)

enable_testing()
add_test(NAME test_readstat COMMAND test_readstat)
