cmake_minimum_required(VERSION 3.15)
project(test_spice_server C)

# 消费者视角：find_package() 证明 spice-server 包（含 spice-protocol 传递头）可用。
find_package(spice-server REQUIRED)

# 消费契约测试：链接导出库，真实调用 libspice-server 的公开 API。
add_executable(test_spice_server_api test_spice_server_api.c)
target_link_libraries(test_spice_server_api PRIVATE
    spice-server::spice-server)

# 鸿蒙特有测试 #1：包内 libspice-server.so 带 OHOS aarch64 / musl / libc++ 平台特征，
# 且 OHOS 加载器可 dlopen 解析。
add_executable(test_ohos_platform test_ohos_platform.c)
target_link_libraries(test_ohos_platform PRIVATE
    spice-server::spice-server
    ${CMAKE_DL_LIBS})

# 鸿蒙特有测试 #2：整条 DT_NEEDED 运行时闭包（glib/pixman/openssl/libjpeg/zlib/lz4/
# libc++/libc）在 OHOS 加载器下可解析，且契约符号经 loader 路径可调用。
add_executable(test_ohos_runtime test_ohos_runtime.c)
target_link_libraries(test_ohos_runtime PRIVATE
    spice-server::spice-server
    ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_spice_server_api COMMAND test_spice_server_api)
add_test(NAME test_ohos_platform COMMAND test_ohos_platform)
add_test(NAME test_ohos_runtime COMMAND test_ohos_runtime)
