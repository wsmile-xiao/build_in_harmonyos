cmake_minimum_required(VERSION 3.15)
project(test_onigmo C)

# Find the package via Conan-generated CMakeDeps
find_package(onigmo REQUIRED)

add_executable(test_onigmo test.c)
target_link_libraries(test_onigmo onigmo::onigmo)

enable_testing()
add_test(NAME test_onigmo COMMAND test_onigmo)
