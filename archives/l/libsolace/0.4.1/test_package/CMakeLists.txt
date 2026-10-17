cmake_minimum_required(VERSION 3.15)
project(test_libsolace CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 消费者视角：只用 conan 生成的导入目标 + 已安装包头，不引用上游源码树。
find_package(libsolace CONFIG REQUIRED)

add_executable(test_libsolace test_libsolace.cpp)
target_link_libraries(test_libsolace PRIVATE libsolace::libsolace)
target_compile_features(test_libsolace PRIVATE cxx_std_17)
