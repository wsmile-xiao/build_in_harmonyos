cmake_minimum_required(VERSION 3.15)
project(mcap_test_package CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(mcap CONFIG REQUIRED)
find_package(lz4 CONFIG REQUIRED)
find_package(zstd CONFIG REQUIRED)

add_executable(test_mcap test_mcap.cpp)
target_link_libraries(test_mcap PRIVATE mcap::mcap lz4::lz4 zstd::libzstd)

add_executable(test_mcap_ohos test_mcap_ohos.cpp)
target_link_libraries(test_mcap_ohos PRIVATE mcap::mcap lz4::lz4 zstd::libzstd)
