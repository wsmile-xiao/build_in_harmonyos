cmake_minimum_required(VERSION 3.16)
project(Qt6LinguistToolsTest LANGUAGES CXX)

# 验证 find_package(Qt6 COMPONENTS Core LinguistTools) 可解析 Qt6::LinguistTools 与 Qt6::Core
find_package(Qt6 6.11 CONFIG REQUIRED COMPONENTS Core LinguistTools)

add_executable(test_qt6linguist test_qt6linguist.cpp)
target_link_libraries(test_qt6linguist PRIVATE Qt6::Core)

# lrelease 实际调用由 test_package/conanfile.py 的 test() 执行（TS -> QM），
# 此处仅保证 Qt6::LinguistTools 宏模块可被 find_package 解析（无空壳）。
