cmake_minimum_required(VERSION 3.15)
project(test_addrwatch_mysql C)

# Find the package via Conan-generated CMakeDeps
find_package(addrwatch-mysql REQUIRED)

add_executable(test_addrwatch_mysql test.c)
target_link_libraries(test_addrwatch_mysql addrwatch-mysql::addrwatch-mysql)

enable_testing()
add_test(NAME test_addrwatch_mysql COMMAND test_addrwatch_mysql)
