cmake_minimum_required(VERSION 3.16)
project(test_knewstuff LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
include(${CMAKE_BINARY_DIR}/generators/conan_cmakedeps_paths.cmake OPTIONAL)

find_package(Qt6 REQUIRED Core Gui Widgets)
find_package(KF6NewStuffCore REQUIRED)
find_package(KF6NewStuff REQUIRED)

add_executable(test_knewstuff test.cpp)
target_link_libraries(
    test_knewstuff
    PRIVATE
        Qt6::Core
        Qt6::Gui
        Qt6::Widgets
        KF6::NewStuffCore
        KF6::NewStuffWidgets
)

enable_testing()
add_test(NAME test_knewstuff COMMAND test_knewstuff)
