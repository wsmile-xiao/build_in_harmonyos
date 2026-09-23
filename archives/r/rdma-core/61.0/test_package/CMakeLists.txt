cmake_minimum_required(VERSION 3.15)
project(test_rdma-core C)

# OHOS E119: 与主配方一致，注入 __MUSL__ 避免 sys/socket.h 与
# linux/socket.h 的 sockaddr_storage 重定义（test_ohos_specific 同 TU 包含两者）
add_compile_definitions(__MUSL__=1)

# Find the package via Conan-generated CMakeDeps
find_package(rdma-core REQUIRED)

# OHOS 运行期动态加载器对部分包内共享库 dlopen 报 EACCES（平台限制），
# 测试二进制改为直接静态链接包内 .a，消除运行期共享库加载依赖。
set(RDMA_CORE_STATIC_LIBS
    ${rdma-core_PACKAGE_FOLDER_RELEASE}/lib/libibverbs.a
    ${rdma-core_PACKAGE_FOLDER_RELEASE}/lib/librdmacm.a
    ${rdma-core_PACKAGE_FOLDER_RELEASE}/lib/libibumad.a
    ${rdma-core_PACKAGE_FOLDER_RELEASE}/lib/libibmad.a
    ${rdma-core_PACKAGE_FOLDER_RELEASE}/lib/libibnetdisc.a)

# L1 基础测试: 消费者视角调用 libibverbs + librdmacm 公共 API
add_executable(test_rdma-core test.c)
target_include_directories(test_rdma-core PRIVATE ${rdma-core_INCLUDE_DIRS_RELEASE})
target_link_libraries(test_rdma-core ${RDMA_CORE_STATIC_LIBS} pthread)

# HarmonyOS 专项测试: 验证 OHOS musl 适配点 (E119/getpass/strrchr/__progname/E513)
add_executable(test_ohos_specific test_ohos_specific.c)
target_link_libraries(test_ohos_specific pthread)

# 消费者用例: 模拟业务上层组件, 仅用公开头文件与公开 API
add_executable(test_consumer test_consumer.c)
target_include_directories(test_consumer PRIVATE ${rdma-core_INCLUDE_DIRS_RELEASE})
target_link_libraries(test_consumer ${RDMA_CORE_STATIC_LIBS} pthread)

enable_testing()
add_test(NAME test_rdma-core COMMAND test_rdma-core)
add_test(NAME test_ohos_specific COMMAND test_ohos_specific)
add_test(NAME test_consumer COMMAND test_consumer)
