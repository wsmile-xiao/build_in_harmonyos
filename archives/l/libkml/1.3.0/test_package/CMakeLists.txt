cmake_minimum_required(VERSION 3.15)
project(test_libkml LANGUAGES CXX)

find_package(libkml REQUIRED)

add_executable(test_libkml test_libkml.cpp)
target_link_libraries(test_libkml libkml::libkml)

# HarmonyOS-specific consumer test for the adapted temp-file path.
add_executable(test_ohos_tempfile test_ohos_tempfile.cpp)
target_link_libraries(test_ohos_tempfile libkml::libkml)

enable_testing()
add_test(NAME test_libkml COMMAND test_libkml)
add_test(NAME test_ohos_tempfile COMMAND test_ohos_tempfile)