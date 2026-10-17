cmake_minimum_required(VERSION 3.16)
project(test_qtscxml LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Scxml StateMachine)

add_executable(test_qtscxml test_qtscxml.cpp)
target_compile_features(test_qtscxml PRIVATE cxx_std_17)
target_link_libraries(
    test_qtscxml
    PRIVATE Qt6::Scxml Qt6::StateMachine
)
