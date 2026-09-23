cmake_minimum_required(VERSION 3.6)
project(test_liblastfm LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_AUTOMOC ON)

find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Network Xml)
find_package(lastfm5 REQUIRED)

# 上游 install(EXPORT lastfm5Config) 只导出 LASTFM::lastfm5 目标，不带
# INTERFACE_INCLUDE_DIRECTORIES（头安装在 <prefix>/include/lastfm5/，
# config 未声明）——通过 lastfm5_INCLUDE_DIR hint 变量（由 test_package
# conanfile.py 的 CMAKE_PREFIX_PATH 注入 package include 根）find_path
find_path(LASTFM5_INCLUDE_DIR
    NAMES lastfm5/global.h
    HINTS ${CMAKE_PREFIX_PATH}
    PATH_SUFFIXES include
    REQUIRED)

add_executable(test_liblastfm test.cpp)
target_include_directories(test_liblastfm PRIVATE ${LASTFM5_INCLUDE_DIR})
target_link_libraries(test_liblastfm PRIVATE Qt5::Core Qt5::Network Qt5::Xml LASTFM::lastfm5)
