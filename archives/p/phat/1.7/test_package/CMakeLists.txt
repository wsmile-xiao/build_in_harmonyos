cmake_minimum_required(VERSION 3.16)
project(phat_test_package LANGUAGES CXX)

find_package(phat CONFIG REQUIRED)

add_executable(test_phat test_phat.cpp)
target_compile_features(test_phat PRIVATE cxx_std_11)
target_link_libraries(test_phat PRIVATE phat::phat)

add_executable(test_phat_ohos test_phat_ohos.cpp)
target_compile_features(test_phat_ohos PRIVATE cxx_std_11)
target_link_libraries(test_phat_ohos PRIVATE phat::phat)
