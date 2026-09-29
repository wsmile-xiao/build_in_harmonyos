cmake_minimum_required(VERSION 3.15)
project(test_rc_ptr CXX)

# rc_ptr 要求 C++17（上游根 CMakeLists: CMAKE_CXX_STANDARD 17）
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 通过 Conan CMakeDeps 消费交付的包
find_package(rc_ptr REQUIRED)

add_executable(test_rc_ptr test_rc_ptr.cpp)
target_link_libraries(test_rc_ptr rc_ptr::rc_ptr)

# 交付进包的 include/ 绝对路径：测试程序据此断言「交付的那一份」头文件内容
target_compile_definitions(test_rc_ptr
    PRIVATE RC_PTR_PKG_INCLUDE_DIR="${RC_PTR_PKG_INCLUDE_DIR}")
