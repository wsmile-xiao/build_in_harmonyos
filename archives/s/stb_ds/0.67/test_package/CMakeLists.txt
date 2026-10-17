cmake_minimum_required(VERSION 3.15)
project(test_stb_ds C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(stb_ds REQUIRED)

# 消费者测试（调用 stb_ds 实际 API）
add_executable(test_stb_ds test.c)
target_link_libraries(test_stb_ds stb::ds)

# 上游测试 test_ds.c（DS_TEST 模式：STBDS_UNIT_TESTS + STBDS_SMALL_BUCKET + churn 压力测试）
# 注意：上游 stb_ds.h 的 STBDS_ADDRESSOF 宏在 clang C 模式（literal array 路径）下
# 对数组 key 有固有限制（上游注释 "currently broken for clang"），故以 C++ 模式编译
add_executable(test_ds test_ds.c)
set_source_files_properties(test_ds.c PROPERTIES LANGUAGE CXX)
target_compile_definitions(test_ds PRIVATE DS_TEST)
target_link_libraries(test_ds stb::ds)

# 上游测试 test_ds_cpp.cpp（C++ 模式：STBDS_UNIT_TESTS + churn 压力测试）
add_executable(test_ds_cpp test_ds_cpp.cpp)
target_compile_definitions(test_ds_cpp PRIVATE DS_TEST)
target_link_libraries(test_ds_cpp stb::ds)

# 上游统计模式 test_ds.c（DS_STATS：STBDS_STATISTICS 探针统计，8 组 500000 项）
add_executable(test_ds_stats test_ds.c)
set_source_files_properties(test_ds.c PROPERTIES LANGUAGE CXX)
target_compile_definitions(test_ds_stats PRIVATE DS_STATS)
target_link_libraries(test_ds_stats stb::ds)

enable_testing()
add_test(NAME test_stb_ds COMMAND test_stb_ds)
add_test(NAME test_ds COMMAND test_ds)
add_test(NAME test_ds_cpp COMMAND test_ds_cpp)
add_test(NAME test_ds_stats COMMAND test_ds_stats)
