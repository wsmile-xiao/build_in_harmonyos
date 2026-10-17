cmake_minimum_required(VERSION 3.15)
project(test_blaspp CXX)

# find_package(blaspp)：与下游 lapackpp 的消费路径一致；
# CMakeDeps 按 recipe 声明的 cmake_file_name=blaspp 生成包配置
find_package(blaspp CONFIG REQUIRED)

add_executable(test_blaspp test_blaspp.cpp)
target_link_libraries(test_blaspp PRIVATE blaspp::blaspp)
target_compile_features(test_blaspp PRIVATE cxx_std_17)

enable_testing()
add_test(NAME blaspp_consumer COMMAND test_blaspp)
