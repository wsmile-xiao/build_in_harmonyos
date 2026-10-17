cmake_minimum_required(VERSION 3.15)
project(test_hlslpp CXX)

# 以消费者身份经 Conan 生成的 CMakeDeps 查找 hlslpp 包
find_package(hlslpp REQUIRED)

add_executable(test_hlslpp test_hlslpp.cpp)
target_link_libraries(test_hlslpp hlslpp::hlslpp)
target_compile_features(test_hlslpp PRIVATE cxx_std_17)
# 上游 premake 默认打开变换矩阵 API（HLSLPP_FEATURE_TRANSFORM）
target_compile_definitions(test_hlslpp PRIVATE HLSLPP_FEATURE_TRANSFORM)

enable_testing()
add_test(NAME test_hlslpp COMMAND test_hlslpp)
