cmake_minimum_required(VERSION 3.16)
project(test_fcitx5_utils LANGUAGES CXX)

find_package(Fcitx5Utils 5.1.13 REQUIRED)

add_executable(test_fcitx5_utils test_fcitx5_utils.cpp)
target_link_libraries(test_fcitx5_utils PRIVATE Fcitx5::Utils)

enable_testing()
add_test(NAME fcitx5_utils_api COMMAND test_fcitx5_utils)