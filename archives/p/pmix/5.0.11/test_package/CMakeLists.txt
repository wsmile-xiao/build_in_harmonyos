cmake_minimum_required(VERSION 3.15)
project(test_pmix C)

# Find the package via Conan-generated CMakeDeps
find_package(pmix REQUIRED)

add_executable(test_pmix test_pmix.c)
target_link_libraries(test_pmix pmix::pmix)

enable_testing()
add_test(NAME test_pmix COMMAND test_pmix)
