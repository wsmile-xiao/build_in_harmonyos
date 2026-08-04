cmake_minimum_required(VERSION 3.15)
project(test_optional_lite CXX)

find_package(optional-lite REQUIRED)

add_executable(test_optional_lite test_optional_lite.cpp)
target_link_libraries(test_optional_lite PRIVATE nonstd::optional-lite)
set_target_properties(test_optional_lite PROPERTIES CXX_STANDARD 17)
