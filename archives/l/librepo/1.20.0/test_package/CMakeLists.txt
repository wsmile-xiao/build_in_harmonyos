cmake_minimum_required(VERSION 3.15)
project(test_librepo C)

# Find the package via Conan-generated CMakeDeps
find_package(librepo REQUIRED)

add_executable(test_librepo test.c)
target_link_libraries(test_librepo librepo::librepo)

enable_testing()
add_test(NAME test_librepo COMMAND test_librepo)
