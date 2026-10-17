cmake_minimum_required(VERSION 3.22)
project(test_swiftshader C)

find_package(SwiftShader REQUIRED)

add_executable(test_swiftshader test_swiftshader.c)
target_link_libraries(test_swiftshader PRIVATE SwiftShader::SwiftShader)
