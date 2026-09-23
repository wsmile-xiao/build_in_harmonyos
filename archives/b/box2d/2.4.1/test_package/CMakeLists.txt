cmake_minimum_required(VERSION 3.8)
project(test_box2d LANGUAGES CXX)

find_package(box2d CONFIG REQUIRED)

add_executable(test_box2d test_package.cpp)
target_link_libraries(test_box2d PRIVATE box2d::box2d)
set_target_properties(test_box2d PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)

enable_testing()
add_test(NAME test_box2d COMMAND test_box2d)
