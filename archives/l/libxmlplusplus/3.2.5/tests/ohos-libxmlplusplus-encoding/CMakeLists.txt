cmake_minimum_required(VERSION 3.16)
project(ohos_libxmlplusplus_encoding CXX)

find_package(PkgConfig REQUIRED)
# 仅通过 libxml++ 已安装/导出的公开 pc（libxml++-3.0）解析编译/链接参数。
pkg_check_modules(XMLXX REQUIRED IMPORTED_TARGET libxml++-3.0)

add_executable(ohos-libxmlplusplus-encoding main.cpp)
target_link_libraries(ohos-libxmlplusplus-encoding PRIVATE PkgConfig::XMLXX)
