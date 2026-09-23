cmake_minimum_required(VERSION 3.15)
project(test_soplex CXX)

# Find the package via Conan-generated CMakeDeps
find_package(soplex REQUIRED)

add_executable(test_soplex test_soplex.cpp)
target_link_libraries(test_soplex soplex::soplex)
target_compile_features(test_soplex PRIVATE cxx_std_11)

# HarmonyOS 专项测试：平台属性（aarch64-ohos ELF）+ 公开 API 求解
add_executable(test_ohos_soplex test_ohos_soplex.cpp)
target_link_libraries(test_ohos_soplex soplex::soplex)
target_compile_features(test_ohos_soplex PRIVATE cxx_std_11)
