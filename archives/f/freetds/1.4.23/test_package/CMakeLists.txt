cmake_minimum_required(VERSION 3.15)
project(test_freetds C)

# Find the package via Conan-generated CMakeDeps
find_package(freetds REQUIRED)

add_executable(test_freetds test.c)
target_link_libraries(test_freetds freetds::freetds)

enable_testing()
add_test(NAME test_freetds COMMAND test_freetds)
