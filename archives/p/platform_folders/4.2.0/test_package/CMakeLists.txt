cmake_minimum_required(VERSION 3.15)
project(test_platform_folders LANGUAGES CXX)

find_package(platform_folders CONFIG REQUIRED)

add_executable(test_platform_folders test_platform_folders.cpp)
target_compile_features(test_platform_folders PRIVATE cxx_std_11)
target_link_libraries(test_platform_folders PRIVATE sago::platform_folders)
