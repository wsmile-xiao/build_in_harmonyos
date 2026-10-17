cmake_minimum_required(VERSION 3.15)
project(libdjconsole_consumer LANGUAGES CXX)

enable_testing()
find_package(libdjconsole CONFIG REQUIRED)

add_executable(test_libdjconsole test_libdjconsole.cpp)
target_link_libraries(test_libdjconsole PRIVATE libdjconsole::libdjconsole)
add_test(NAME libdjconsole_consumer COMMAND test_libdjconsole)
