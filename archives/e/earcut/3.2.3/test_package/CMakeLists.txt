cmake_minimum_required(VERSION 3.15)
project(test_earcut CXX)

find_package(earcut_hpp REQUIRED)

add_executable(test_earcut test_earcut.cpp)
target_link_libraries(test_earcut PRIVATE earcut_hpp::earcut_hpp)
set_target_properties(test_earcut PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON)

add_executable(test_earcut_ohos test_earcut_ohos.cpp)
target_link_libraries(test_earcut_ohos PRIVATE earcut_hpp::earcut_hpp)
set_target_properties(test_earcut_ohos PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON)