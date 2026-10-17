cmake_minimum_required(VERSION 3.15)
project(test_libcec C)

# Find the package via Conan-generated CMakeDeps
find_package(libcec REQUIRED)

add_executable(test_libcec test.c)
target_link_libraries(test_libcec libcec::libcec)

add_executable(test_libcec_ohos test_ohos.c)
target_link_libraries(test_libcec_ohos libcec::libcec)

# 上游功能检查：12 项无硬件确定性检查（公开 C API + cecc-client --info 真执行）。
# CECC_CLIENT_BIN 由 test_package/conanfile.py build() 透传已安装包内绝对路径；
# 未透传时二进制在运行时走 PATH 回退查找 cecc-client。
if(NOT DEFINED CECC_CLIENT_BIN)
  set(CECC_CLIENT_BIN "")
endif()
add_executable(test_upstream_checks test_upstream_checks.c)
target_link_libraries(test_upstream_checks libcec::libcec)
target_compile_definitions(test_upstream_checks PRIVATE CECC_CLIENT_BIN="${CECC_CLIENT_BIN}")

enable_testing()
add_test(NAME test_libcec COMMAND test_libcec)
add_test(NAME test_libcec_ohos COMMAND test_libcec_ohos)
add_test(NAME upstream_checks COMMAND test_upstream_checks)