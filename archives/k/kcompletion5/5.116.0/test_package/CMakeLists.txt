cmake_minimum_required(VERSION 3.16)
project(test_kcompletion5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 5.15.2 CONFIG REQUIRED COMPONENTS Widgets Test)
find_package(KF5Completion 5.116.0 CONFIG REQUIRED)

add_executable(test_kcompletion5 test.cpp)
target_compile_definitions(test_kcompletion5 PRIVATE
    QT_CORE_LIB
    QT_GUI_LIB
    QT_WIDGETS_LIB
    QT_TEST_LIB
)
target_link_libraries(test_kcompletion5 PRIVATE Qt5::Widgets Qt5::Test KF5::Completion)

enable_testing()
add_test(NAME test_kcompletion5 COMMAND test_kcompletion5)
