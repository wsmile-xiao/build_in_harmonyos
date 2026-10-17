cmake_minimum_required(VERSION 3.15)
project(mediainfo_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(MediaInfoLib CONFIG REQUIRED)
add_executable(mediainfo_test test.cpp)
# UNICODE build of the vendored ZenLib API (Ztring/String are std::wstring)
target_compile_definitions(mediainfo_test PRIVATE UNICODE _UNICODE)
target_link_libraries(mediainfo_test PRIVATE mediainfo)
