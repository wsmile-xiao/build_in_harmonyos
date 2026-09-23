cmake_minimum_required(VERSION 3.23)
project(liblsl_consumer_test LANGUAGES C CXX)

# 消费者视角：只通过安装出的 Conan 包配置来使用 liblsl
# （CMakeDeps 依据 package_info() 的 cmake_file_name/cmake_target_name 生成
#   LSLConfig.cmake + LSL::lsl IMPORTED 目标）。
find_package(LSL CONFIG REQUIRED)

# C API 消费者
add_executable(test_liblsl_c test_c.c)
target_link_libraries(test_liblsl_c PRIVATE LSL::lsl)
set_target_properties(test_liblsl_c PROPERTIES
    C_STANDARD 11
    C_STANDARD_REQUIRED ON
)

# C++ API 消费者（lsl_cpp.h 需要 C++17）
add_executable(test_liblsl_cpp test_cpp.cpp)
target_link_libraries(test_liblsl_cpp PRIVATE LSL::lsl)
set_target_properties(test_liblsl_cpp PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
)
