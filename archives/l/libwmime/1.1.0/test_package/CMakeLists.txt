cmake_minimum_required(VERSION 3.15)
project(libwmime_test_package CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(wmime REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(Iconv QUIET)

add_executable(test_message_build test_message_build.cpp)
target_link_libraries(test_message_build PRIVATE wmime::wmime)

add_executable(test_mime_parse test_mime_parse.cpp)
target_link_libraries(test_mime_parse PRIVATE wmime::wmime)

include(CTest)
add_test(NAME message_build COMMAND test_message_build)
add_test(NAME mime_parse COMMAND test_mime_parse)
