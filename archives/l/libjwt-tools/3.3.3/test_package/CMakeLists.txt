cmake_minimum_required(VERSION 3.15)
project(test_libjwt_tools C)

# 消费者视角：经 libjwt-tools 的 requires 链拿到 libjwt（传递依赖）
find_package(libjwt REQUIRED)

add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer libjwt::libjwt)

add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos ${CMAKE_DL_LIBS})
# 鸿蒙（OHOS）特有消费者用例：验证 libjwt-tools 交付的 4 个命令行工具
# 经 Conan 的 bindirs 通道可达，且为合法的 OHOS aarch64 可执行文件。
# 目录由 conanfile.py 的 generate() 经 -DLIBJWT_TOOLS_BINDIR=... 注入。
if(NOT DEFINED LIBJWT_TOOLS_BINDIR)
  set(LIBJWT_TOOLS_BINDIR "/nonexistent-libjwt-tools-bindir")
endif()
target_compile_definitions(test_ohos PRIVATE
  LIBJWT_TOOLS_BINDIR="${LIBJWT_TOOLS_BINDIR}")

enable_testing()
add_test(NAME test_consumer COMMAND test_consumer)
add_test(NAME test_ohos COMMAND test_ohos)
