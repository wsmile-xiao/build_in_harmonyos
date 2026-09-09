cmake_minimum_required(VERSION 3.15)
project(curl_consumer LANGUAGES C)

find_package(CURL CONFIG REQUIRED)

add_executable(test_curl test.c)
target_link_libraries(test_curl PRIVATE CURL::libcurl)
