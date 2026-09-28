cmake_minimum_required(VERSION 3.15)
project(test_libaesgm C)

# Find the package via Conan-generated CMakeDeps
find_package(libaesgm REQUIRED)

add_executable(test_libaesgm test.c)
target_link_libraries(test_libaesgm libaesgm::libaesgm)

enable_testing()
add_test(NAME test_libaesgm COMMAND test_libaesgm)
