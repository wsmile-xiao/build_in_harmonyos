cmake_minimum_required(VERSION 3.15)
project(test_d0_blind_id C)

# 必须在 add_executable() 之前：目录属性在目标创建时快照
add_compile_options(-Wall)

# conan(CMakeDeps) 生成的配置：include/d0_blind_id 下的头 + 两个库
find_package(d0_blind_id CONFIG REQUIRED)

add_executable(test_d0_blind_id test_d0_blind_id.c)
target_link_libraries(test_d0_blind_id PRIVATE d0_blind_id::d0_blind_id)
