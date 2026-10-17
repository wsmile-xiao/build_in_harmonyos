cmake_minimum_required(VERSION 3.15)
project(test_clastfm C)

find_package(libclastfm REQUIRED)
find_package(CURL REQUIRED)

add_executable(test_clastfm test_clastfm.c)
target_link_libraries(test_clastfm PRIVATE libclastfm::libclastfm CURL::libcurl)

enable_testing()
add_test(NAME test_clastfm COMMAND test_clastfm)
