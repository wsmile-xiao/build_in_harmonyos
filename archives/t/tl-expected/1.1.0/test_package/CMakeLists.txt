cmake_minimum_required(VERSION 3.15)
project(test_tl_expected CXX)

find_package(tl-expected REQUIRED)

add_executable(test_tl_expected test_tl_expected_ohos.cpp)
target_link_libraries(test_tl_expected PRIVATE tl::expected)
set_target_properties(test_tl_expected PROPERTIES CXX_STANDARD 17)