cmake_minimum_required(VERSION 3.16)
project(test_ktextwidgets LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
include(${CMAKE_BINARY_DIR}/generators/conan_cmakedeps_paths.cmake OPTIONAL)

find_package(Qt6 REQUIRED Core Widgets)
find_package(KF6TextWidgets REQUIRED)

add_executable(test_ktextwidgets test.cpp)
target_link_libraries(test_ktextwidgets PRIVATE Qt6::Core Qt6::Widgets KF6::TextWidgets)

enable_testing()
add_test(NAME test_ktextwidgets COMMAND test_ktextwidgets)
