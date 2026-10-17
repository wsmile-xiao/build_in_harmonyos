cmake_minimum_required(VERSION 3.15)
project(uni-algo-test-package LANGUAGES CXX)

# 用 conan CMakeDeps 生成的包配置文件；目标名与 cpp_info 里的 cmake_target_name 一致。
# 找不到包 / 找不到头 / 链不到 lib/libuni-algo.a 都会在 configure|build 阶段直接失败，
# 这正是 L1e 破坏性反向验证（把 include/ 与 lib/ 整体移走）要看到的红。
find_package(uni-algo CONFIG REQUIRED)

add_executable(consumer_probe consumer.cpp)
target_link_libraries(consumer_probe PRIVATE uni-algo::uni-algo)
target_compile_features(consumer_probe PRIVATE cxx_std_17)

add_executable(ohos_probe test_ohos.cpp)
target_link_libraries(ohos_probe PRIVATE uni-algo::uni-algo)
target_compile_features(ohos_probe PRIVATE cxx_std_17)
