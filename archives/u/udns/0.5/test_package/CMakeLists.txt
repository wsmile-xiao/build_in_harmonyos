cmake_minimum_required(VERSION 3.15)
project(test_udns C)

# Find the library via Conan-generated CMakeDeps
find_package(udns CONFIG REQUIRED)

# 层 1：CMake 消费者（离线确定性断言 + 端到端异步解析回环）
add_executable(test_udns test.c)
target_link_libraries(test_udns udns::udns)

# 层 3：鸿蒙特有测试（rule 12）—— libudns 在 OHOS/aarch64 上的完整消费者
# 生命周期闭环：dns_init -> dns_add_serv/dns_open -> dns_submit_a4 ->
# poll + dns_ioevent -> RR 解码回调 -> dns_ntop 渲染 -> dns_close。
# 内置一个最小 UDP DNS 应答器线程，使无外网的设备也能确定性走通
# 「查询编码 → sendto → 应答接收 → DNS 报文解析 → RR 解码 → 回调派发」
# 全链路，因此需要 pthread。
# 层 2 的 test_static_link 由 test_package/conanfile.py 用 profile 的 CC 直接
# 链接 libudns.a 编译（刻意不经 CMakeDeps），故不在此声明。
add_executable(test_udns_ohos test_udns_ohos.c)

# 用工具链的 -lpthread 直接链接，而不是 find_package(Threads)：Threads 是
# CMake 的宿主侧探测，交叉场景下可能解析失败，使层 3 静默 SKIP 或表现为
# 别的目标构建失败。OHOS sysroot 提供 libpthread，直接链接与之等价。
# （已知局限：若某 sysroot 把 pthread 并入 libc 且不提供 libpthread.so，
#   此处会链接失败 —— 届时应改为探测后降级，与本版本适配器无关。）
# 加 compiler-id 守卫：非 GNU/Clang 系工具链不认 -pthread / -lpthread，
# 无条件传入会让层 3 编译失败，并**连带层 1 的 test_udns 一起构建失败** ——
# 那时 CI 报的是"CMake 构建失败"，归因会指向错误的目标。
target_compile_options(test_udns_ohos PRIVATE
    $<$<C_COMPILER_ID:GNU,Clang,AppleClang>:-pthread>)
target_link_libraries(test_udns_ohos PRIVATE udns::udns
    $<$<C_COMPILER_ID:GNU,Clang,AppleClang>:-lpthread>)
