cmake_minimum_required(VERSION 3.15)
project(test_linux_atm C)

# Find the package via the Conan-generated CMakeDeps config
find_package(linux-atm REQUIRED)

add_executable(test_linux_atm test.c)
target_link_libraries(test_linux_atm linux-atm::linux-atm)

enable_testing()
add_test(NAME test_linux_atm COMMAND test_linux_atm)
