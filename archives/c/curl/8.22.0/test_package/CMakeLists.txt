cmake_minimum_required(VERSION 3.15)
project(curl_test C)

find_package(CURL REQUIRED)
add_executable(curl_test test.c)
target_link_libraries(curl_test PRIVATE CURL::libcurl)

enable_testing()
add_test(NAME curl_test COMMAND curl_test)
