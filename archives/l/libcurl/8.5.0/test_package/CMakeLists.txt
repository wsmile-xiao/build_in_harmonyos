cmake_minimum_required(VERSION 3.15)
project(test_libcurl C)

find_package(CURL REQUIRED CONFIG)

add_executable(test_libcurl test_libcurl.c)
target_link_libraries(test_libcurl PRIVATE CURL::libcurl)

enable_testing()
add_test(NAME libcurl_test COMMAND test_libcurl)
