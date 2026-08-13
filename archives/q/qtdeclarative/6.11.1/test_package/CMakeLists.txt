cmake_minimum_required(VERSION 3.16)
project(test_qtdeclarative LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Qml)

add_executable(test_qtdeclarative test_qtdeclarative.cpp)
target_compile_features(test_qtdeclarative PRIVATE cxx_std_17)
target_link_libraries(
    test_qtdeclarative
    PRIVATE Qt6::Qml Qt6::Core
)
