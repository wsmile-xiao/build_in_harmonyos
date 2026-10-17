cmake_minimum_required(VERSION 3.18)
project(test_arg_router CXX)

# 消费者视角：只能靠 CMakeDeps 生成的 arg_router-config.cmake 找到包
find_package(arg_router REQUIRED)

add_executable(test_arg_router test_arg_router.cpp)
target_link_libraries(test_arg_router PRIVATE arg_router::arg_router)

# 消费者按**上游默认配置**编译：C++17 + span-lite（上游 vcpkg.json 明列 span-lite、
# .github/workflows/pr_checker.yml:155 以 -DCMAKE_CXX_STANDARD=17 构建
# arg_router_test cpp17_examples）。用 cxx_std_17 而非 20，等于顺带验证
# 「库声明的最低标准 C++17 + span-lite」这条消费路径。
target_compile_features(test_arg_router PRIVATE cxx_std_17)
set_target_properties(test_arg_router PROPERTIES CXX_EXTENSIONS OFF)

enable_testing()
add_test(NAME test_arg_router COMMAND test_arg_router)
