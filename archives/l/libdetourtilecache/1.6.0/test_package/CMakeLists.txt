cmake_minimum_required(VERSION 3.16)
project(libdetourtilecache_test CXX)

find_package(libdetourtilecache REQUIRED CONFIG)
add_executable(libdetourtilecache_test test_detour_tile_cache.cpp)
target_link_libraries(libdetourtilecache_test PRIVATE libdetourtilecache::libdetourtilecache)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_compile_definitions(libdetourtilecache_test PRIVATE LIBDETOURTILECACHE_HARMONYOS=1)
endif()
