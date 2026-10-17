cmake_minimum_required(VERSION 3.15)
project(test_libmodsecurity C)

find_package(modsecurity REQUIRED)

add_executable(test_modsecurity test_modsecurity.c)
target_link_libraries(test_modsecurity PRIVATE modsecurity::modsecurity)

add_executable(test_waf_block test_waf_block.c)
target_link_libraries(test_waf_block PRIVATE modsecurity::modsecurity)

enable_testing()
add_test(NAME modsecurity_c_api COMMAND test_modsecurity)
add_test(NAME modsecurity_waf_block COMMAND test_waf_block)
