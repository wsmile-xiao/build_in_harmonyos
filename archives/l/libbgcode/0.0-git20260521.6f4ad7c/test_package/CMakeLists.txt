cmake_minimum_required(VERSION 3.15)
project(libbgcode_test_package CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

enable_testing()

find_package(LibBGCode REQUIRED)

add_executable(convert_contract convert_contract.cpp)
target_link_libraries(convert_contract PRIVATE
    LibBGCode::bgcode_convert
    LibBGCode::bgcode_binarize
    LibBGCode::bgcode_core)
add_test(NAME convert_contract COMMAND convert_contract)

add_executable(core_contract core_contract.cpp)
target_link_libraries(core_contract PRIVATE
    LibBGCode::bgcode_binarize
    LibBGCode::bgcode_core)
add_test(NAME core_contract COMMAND core_contract)
