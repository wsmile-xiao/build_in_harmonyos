cmake_minimum_required(VERSION 3.12)
project(test_openjph CXX)

find_package(openjph REQUIRED)

add_executable(test_openjph test_openjph.cpp)
# 上游 install(EXPORT openjph-targets) 无 NAMESPACE，target 为裸名 openjph；
# Conan CMakeDeps 按 cmake_target_name="openjph" 生成同名 target
target_link_libraries(test_openjph openjph)