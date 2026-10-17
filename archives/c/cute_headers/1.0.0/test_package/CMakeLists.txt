cmake_minimum_required(VERSION 3.15)
project(test_package C CXX)

find_package(cute_headers CONFIG REQUIRED)

add_executable(test_cute_headers test_cute_headers.c)
target_link_libraries(test_cute_headers PRIVATE cute_headers::cute_headers)
target_compile_features(test_cute_headers PRIVATE c_std_11)

add_executable(test_cute_tiled test_cute_tiled.cpp)
target_link_libraries(test_cute_tiled PRIVATE cute_headers::cute_headers)
target_compile_features(test_cute_tiled PRIVATE cxx_std_11)
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/test_cute_tiled.json"
    "${CMAKE_CURRENT_BINARY_DIR}/test_cute_tiled.json"
    COPYONLY
)