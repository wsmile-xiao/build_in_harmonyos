cmake_minimum_required(VERSION 3.16)
project(coinutils_smoke CXX)

# Conan CMakeDeps provides the coinutils target and its transitive dependencies.
find_package(coinutils REQUIRED CONFIG)

add_executable(coinutils_smoke coinutils_smoke.cpp)
target_link_libraries(coinutils_smoke PRIVATE coinutils::coinutils)

# 鸿蒙 aarch64 默认静态链接，避免目标机缺 .so
set_target_properties(coinutils_smoke PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    LINK_SEARCH_START_STATIC ON
)
