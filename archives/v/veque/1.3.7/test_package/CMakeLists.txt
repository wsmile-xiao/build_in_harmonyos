cmake_minimum_required(VERSION 3.15)
project(test_veque CXX)

# 消费者视角：只经由 Conan CMakeDeps 找到已打包的 veque 头文件
find_package(veque REQUIRED)

add_executable(test_veque test.cpp)
target_link_libraries(test_veque veque::veque)
# veque 要求 C++17（README / 配方 validate() 同口径）
target_compile_features(test_veque PRIVATE cxx_std_17)
