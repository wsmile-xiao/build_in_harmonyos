cmake_minimum_required(VERSION 3.15)
project(libmdbx_consumer LANGUAGES C CXX)

find_package(libmdbx CONFIG REQUIRED)

add_executable(test_libmdbx_c test.c)
target_compile_features(test_libmdbx_c PRIVATE c_std_11)
target_link_libraries(test_libmdbx_c PRIVATE libmdbx::mdbx)

add_executable(test_libmdbx_cpp test.cpp)
target_compile_features(test_libmdbx_cpp PRIVATE cxx_std_17)
target_link_libraries(test_libmdbx_cpp PRIVATE libmdbx::mdbx)

if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    add_executable(test_libmdbx_ohos test_ohos.c)
    target_compile_features(test_libmdbx_ohos PRIVATE c_std_11)
    target_link_libraries(test_libmdbx_ohos PRIVATE libmdbx::mdbx)
endif()
