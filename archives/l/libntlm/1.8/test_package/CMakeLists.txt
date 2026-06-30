cmake_minimum_required(VERSION 3.15)
project(test_libntlm C)

# Find the package via Conan-generated CMakeDeps
find_package(libntlm REQUIRED)

add_executable(test_libntlm test.c)
target_link_libraries(test_libntlm libntlm::libntlm)

enable_testing()
add_test(NAME test_libntlm COMMAND test_libntlm)
