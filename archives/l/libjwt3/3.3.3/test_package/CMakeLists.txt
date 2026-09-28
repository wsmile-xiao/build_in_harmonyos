cmake_minimum_required(VERSION 3.15)
project(test_libjwt3 C)

# Find the package via Conan-generated CMakeDeps（目标名由 package_info 的
# cmake_file_name/cmake_target_name 决定：libjwt3::jwt）
find_package(libjwt3 REQUIRED)

add_executable(test_libjwt3 test.c)
target_link_libraries(test_libjwt3 libjwt3::jwt)

# 鸿蒙（OHOS）平台特有测试：SONAME 加载语义 / OpenSSL 静态链入 / POSIX shell 驱动
# / 4 个命令行工具经 Conan bindirs 通道可达（R38）。
# 工具目录由 conanfile.py 的 generate() 经 -DLIBJWT3_BINDIR=... 注入。
if(NOT DEFINED LIBJWT3_BINDIR)
  set(LIBJWT3_BINDIR "/nonexistent-libjwt3-bindir")
endif()
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos libjwt3::jwt ${CMAKE_DL_LIBS})
target_compile_definitions(test_ohos PRIVATE
  LIBJWT3_BINDIR="${LIBJWT3_BINDIR}")

enable_testing()
add_test(NAME test_libjwt3 COMMAND test_libjwt3)
add_test(NAME test_ohos COMMAND test_ohos)
