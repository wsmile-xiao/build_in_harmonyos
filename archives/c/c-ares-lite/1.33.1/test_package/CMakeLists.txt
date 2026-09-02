cmake_minimum_required(VERSION 3.15)
project(test_c-ares-lite C)

# Find the package via Conan-generated CMakeDeps
find_package(c-ares REQUIRED)

add_executable(test_c-ares-lite test.c)
target_link_libraries(test_c-ares-lite c-ares::c-ares)

# 鸿蒙特有测试：真实调用 ares API 验证 OHOS hosts/HMDFS 的 localhost 解析
add_executable(test_c-ares-lite-ohos-hosts test_ohos_hosts.c)
target_link_libraries(test_c-ares-lite-ohos-hosts c-ares::c-ares)

enable_testing()
add_test(NAME test_c-ares-lite COMMAND test_c-ares-lite)
add_test(NAME test_c-ares-lite-ohos-hosts COMMAND test_c-ares-lite-ohos-hosts)