cmake_minimum_required(VERSION 3.16)
project(test_knewstuff LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt6 6.9.0 REQUIRED COMPONENTS Core Gui)
find_package(KF6NewStuffCore 6.18.0 REQUIRED)

add_executable(test_knewstuff test.cpp)
target_link_libraries(test_knewstuff PRIVATE Qt6::Core Qt6::Gui KF6::NewStuffCore)

enable_testing()
add_test(NAME test_knewstuff COMMAND test_knewstuff)
