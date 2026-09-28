cmake_minimum_required(VERSION 3.15)
project(test_copypp CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 消费者视角：只用打包后的 include 与导入目标
find_package(copypp CONFIG REQUIRED)

add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE icurve::copypp)
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_20)
