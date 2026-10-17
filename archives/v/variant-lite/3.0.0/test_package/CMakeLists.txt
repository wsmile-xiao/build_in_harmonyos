cmake_minimum_required(VERSION 3.15)
project(test_variant_lite LANGUAGES CXX)

find_package(variant-lite CONFIG REQUIRED)

add_executable(test_variant_lite test_variant_lite.cpp)
target_link_libraries(test_variant_lite PRIVATE nonstd::variant-lite)
set_target_properties(test_variant_lite PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)
