cmake_minimum_required(VERSION 3.18)
project(test_jsrl CXX)

# 消费者视角：只能靠 CMakeDeps 生成的 jsrl-config.cmake 找到包
find_package(jsrl REQUIRED)

add_executable(test_jsrl test_jsrl.cpp)
target_link_libraries(test_jsrl PRIVATE jsrl::jsrl)

# 消费者按**库声明的最低标准** C++17 编译：等于顺带验证「C++17 消费面」这条路径
# （上游库本体 CMakeLists 默认 CMAKE_CXX_STANDARD=17，测试树同为 17，与上游
#  .github/workflows/ci.yml 同口径）
target_compile_features(test_jsrl PRIVATE cxx_std_17)
set_target_properties(test_jsrl PROPERTIES CXX_EXTENSIONS OFF)

enable_testing()
add_test(NAME test_jsrl COMMAND test_jsrl)
