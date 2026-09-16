cmake_minimum_required(VERSION 3.15)
project(test_package C CXX)

# libint2 由上游 CMake 包配置提供（CMakeDeps 生成 libint2-config.cmake）
find_package(libint2 CONFIG REQUIRED)

# ── 入口 1：C++ API（BasisSet + Engine，重叠矩阵与库仑积分）──
add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE libint2::int2)
target_compile_features(test_package PRIVATE cxx_std_17)
# OHOS：静态链接 C++ 运行时，使测试二进制可直接运行
# （libc++_shared.so 只存在于 SDK sysroot，不在设备默认库搜索路径）
target_link_options(test_package PRIVATE -static-libstdc++)

# ── 入口 2：C API（C ABI：内核分发表 / 内存查询 / init-cleanup 生命周期）──
add_executable(test_c_api test_c_api.c)
target_link_libraries(test_c_api PRIVATE libint2::int2)

# ── 入口 3：基组数据（按名加载 + 未知基组名必须报错）──
add_executable(test_basis test_basis.cpp)
target_link_libraries(test_basis PRIVATE libint2::int2)
target_compile_features(test_basis PRIVATE cxx_std_17)
target_link_options(test_basis PRIVATE -static-libstdc++)

# 入口 4（pkg-config 消费契约）不在此构建：
# test_pkgconfig.c 由 conanfile.py 的 test() 直接用 `pkg-config --cflags/--libs libint2`
# 的返回值编译，用于验证安装出来的 libint2.pc 可用（上游模板渲染缺陷的回归守卫）。
