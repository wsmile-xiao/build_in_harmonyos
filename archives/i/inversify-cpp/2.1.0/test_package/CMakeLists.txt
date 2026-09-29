# 消费者测试 — inversify-cpp 2.1.0（header-only 交付形态）
cmake_minimum_required(VERSION 3.15)
project(test_inversify_cpp CXX)

# 消费者视角：通过 Conan 生成的 CMakeDeps 找到 inversify-cpp 包交付的头文件
find_package(inversify-cpp REQUIRED CONFIG)

add_executable(test_inversify_cpp test_inversify_cpp.cpp)
target_link_libraries(test_inversify_cpp PRIVATE inversify-cpp::inversify-cpp)

# 绑定检视 API（上游 BUILD 的 cc_binary("test") 同款宏，上游测试同样带它编译）
target_compile_definitions(test_inversify_cpp PRIVATE INVERSIFY_BINDING_INSPECTION)

# 上游头部自报 C++17（README / BUILD -std=c++17），与 profile compiler.cppstd=17 同档
set_target_properties(test_inversify_cpp PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF)

enable_testing()
add_test(NAME inversify_cpp_consumer COMMAND test_inversify_cpp)
