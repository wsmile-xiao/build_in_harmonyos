cmake_minimum_required(VERSION 3.15)
project(test_raul CXX)

# 通过 Conan CMakeDeps 找到已安装的 raul 包
find_package(raul REQUIRED)

add_executable(test_raul test_raul.cpp)
target_compile_features(test_raul PRIVATE cxx_std_17)
target_link_libraries(test_raul PRIVATE raul::raul)

enable_testing()
add_test(NAME test_raul COMMAND test_raul)
