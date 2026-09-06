cmake_minimum_required(VERSION 3.16)
project(test_ksyntaxhighlighting LANGUAGES CXX)

find_package(Qt6 CONFIG REQUIRED COMPONENTS Core Gui)
find_package(KF6SyntaxHighlighting CONFIG REQUIRED)

add_executable(test_ksyntaxhighlighting test_ksyntaxhighlighting.cpp)
target_link_libraries(test_ksyntaxhighlighting PRIVATE Qt6::Core Qt6::Gui KF6::SyntaxHighlighting)

enable_testing()
add_test(NAME test_ksyntaxhighlighting COMMAND test_ksyntaxhighlighting)
