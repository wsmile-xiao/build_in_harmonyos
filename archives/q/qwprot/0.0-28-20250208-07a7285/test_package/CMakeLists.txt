cmake_minimum_required(VERSION 3.15)
project(qwprot_test_package LANGUAGES CXX)

find_package(qwprot REQUIRED CONFIG)

add_executable(test_qwprot test_qwprot.cpp)
target_compile_features(test_qwprot PRIVATE cxx_std_17)
target_link_libraries(test_qwprot PRIVATE qwprot::qwprot)
target_link_options(test_qwprot PRIVATE -static)

add_executable(test_qwprot_ohos test_qwprot_ohos.cpp)
target_compile_features(test_qwprot_ohos PRIVATE cxx_std_17)
target_link_libraries(test_qwprot_ohos PRIVATE qwprot::qwprot)
target_link_options(test_qwprot_ohos PRIVATE -static)
