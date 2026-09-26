cmake_minimum_required(VERSION 3.15)
project(libexsid_consumer C)

enable_testing()
find_package(libexsid CONFIG REQUIRED)

add_executable(test_libexsid test.c)
target_link_libraries(test_libexsid PRIVATE libexsid::libexsid)
add_test(NAME libexsid_consumer COMMAND test_libexsid)
