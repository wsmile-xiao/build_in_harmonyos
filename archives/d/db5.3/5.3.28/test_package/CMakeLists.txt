cmake_minimum_required(VERSION 3.15)
project(test_db5 C)

add_compile_options(-Wall)

# conan(CMakeDeps) 生成的配置：include/db.h + libdb-5.3.so
# 包名 db5.3 含 '.'，recipe 里显式把 cmake 文件名/目标名定为 db5_3（见 package_info）
find_package(db5_3 CONFIG REQUIRED)

add_executable(test_db5 test_db5.c)
target_link_libraries(test_db5 PRIVATE db5_3::db5_3)
