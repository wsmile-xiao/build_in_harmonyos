cmake_minimum_required(VERSION 3.16)
project(test_qtshadertools LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS ShaderTools)

add_executable(test_qtshadertools test_qtshadertools.cpp)
target_compile_features(test_qtshadertools PRIVATE cxx_std_17)
target_link_libraries(
    test_qtshadertools
    PRIVATE Qt6::ShaderTools Qt6::Core Qt6::Gui
)
