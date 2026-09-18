cmake_minimum_required(VERSION 3.16)
project(test_ki18n5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core)
find_package(KF5I18n 5.116.0 REQUIRED)

add_executable(test_ki18n5 test.cpp)
target_link_libraries(test_ki18n5 PRIVATE Qt5::Core KF5::I18n)

enable_testing()
add_test(NAME test_ki18n5 COMMAND test_ki18n5)
