cmake_minimum_required(VERSION 3.15)
project(test_barkeep CXX)

# 消费者按上游口径用 C++20 编译（barkeep 上游 meson default_options cpp_std=c++20；
# CI profile 是 compiler.cppstd=17，故在消费者目标上显式要求 cxx_std_20）
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(barkeep REQUIRED)

add_executable(test_barkeep test_package.cpp)
target_link_libraries(test_barkeep barkeep::barkeep)
target_compile_features(test_barkeep PRIVATE cxx_std_20)
