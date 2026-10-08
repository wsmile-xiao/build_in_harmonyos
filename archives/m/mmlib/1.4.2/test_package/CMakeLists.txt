cmake_minimum_required(VERSION 3.15)
project(test_mmlib C)

# 消费者视角：find_package() 证明 mmlib 包（单一无版本 libmmlib.so + 公开头）可用。
find_package(mmlib REQUIRED)

# 消费契约测试：链接导出库，真实调用 mmlib 公开 API。
add_executable(test_mmlib_api test_mmlib_api.c)
target_link_libraries(test_mmlib_api PRIVATE
    mmlib::mmlib)

# 鸿蒙特有测试：包内 libmmlib.so 平台 ABI 实测 + OHOS 加载器 dlopen/dlsym。
add_executable(test_ohos_platform test_ohos_platform.c)
target_link_libraries(test_ohos_platform PRIVATE
    ${CMAKE_DL_LIBS})

# 消费者最小应用管线（E2E）：配置流 / 跨进程数据管线 / 跨进程互斥。
add_executable(test_mmlib_e2e test_mmlib_e2e.c)
target_link_libraries(test_mmlib_e2e PRIVATE
    mmlib::mmlib)

enable_testing()
add_test(NAME test_mmlib_api COMMAND test_mmlib_api)
add_test(NAME test_ohos_platform COMMAND test_ohos_platform)
add_test(NAME test_mmlib_e2e COMMAND test_mmlib_e2e)
