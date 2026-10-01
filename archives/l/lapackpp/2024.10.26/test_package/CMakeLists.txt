cmake_minimum_required(VERSION 3.15)
project(test_lapackpp CXX)

# find_package(lapackpp)：与下游 SLATE 的消费路径一致；
# CMakeDeps 按 recipe 声明的 cmake_file_name=lapackpp 生成包配置
find_package(lapackpp CONFIG REQUIRED)

add_executable(test_lapackpp test_lapackpp.cpp)
target_link_libraries(test_lapackpp PRIVATE lapackpp::lapackpp)
target_compile_features(test_lapackpp PRIVATE cxx_std_17)

enable_testing()
add_test(NAME lapackpp_consumer COMMAND test_lapackpp)
