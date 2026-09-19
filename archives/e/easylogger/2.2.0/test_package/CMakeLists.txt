cmake_minimum_required(VERSION 3.15)
project(test_easylogger C)

# Find the package via Conan-generated CMakeDeps
find_package(easylogger REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_easylogger test.c)
target_link_libraries(test_easylogger easylogger::easylogger Threads::Threads)

enable_testing()
add_test(NAME test_easylogger COMMAND test_easylogger)