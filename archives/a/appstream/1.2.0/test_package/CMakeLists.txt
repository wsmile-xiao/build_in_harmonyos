cmake_minimum_required(VERSION 3.15)
project(test_appstream C)

# 消费者验证：通过 appstream.pc（配方组件 requires 生成的完整 Requires 链）
# 经 pkg-config 递归解析全部传递依赖并链接
find_package(PkgConfig REQUIRED)
pkg_check_modules(APPSTREAM REQUIRED IMPORTED_TARGET appstream)

add_executable(test_appstream test.c)
target_link_libraries(test_appstream PRIVATE PkgConfig::APPSTREAM)

enable_testing()
add_test(NAME test_appstream COMMAND test_appstream)