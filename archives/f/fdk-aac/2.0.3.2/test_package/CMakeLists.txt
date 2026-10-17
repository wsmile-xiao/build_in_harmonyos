cmake_minimum_required(VERSION 3.16)
project(test_fdk_aac C)

find_package(fdk-aac REQUIRED)

# 消费者探针:结构性端到端 + 聚合 SHA-1 输出
add_executable(fdk_aac_probe probe.c upstream-test/sha1.c)
target_link_libraries(fdk_aac_probe PRIVATE fdk-aac::fdk-aac)
target_include_directories(fdk_aac_probe PRIVATE upstream-test)
if(NOT MSVC)
  target_link_libraries(fdk_aac_probe PRIVATE m)
  target_compile_options(fdk_aac_probe PRIVATE -Wall -Wextra -O2)
endif()

# 上游官方测试工具(源文件 vendor 自官方发行包,不随 install 安装,
# 此处与探针同批构建;SHA-1 输出与官方 ref-*.txt 位元比对)
# 上游源用裸 #include "aacenc_lib.h"(发行包构建树内相对路径),vendor 进
# test_package 后需额外把 <pkg-include>/fdk-aac 加入 include 路径;源文件
# 保持与官方逐字节一致,不修改其 include 写法。
get_target_property(FDK_INC_DIRS fdk-aac::fdk-aac INTERFACE_INCLUDE_DIRECTORIES)
list(GET FDK_INC_DIRS 0 FDK_INC)
add_executable(test-encode-decode
  upstream-test/test-encode-decode.c
  upstream-test/wavreader.c
  upstream-test/sha1.c)
target_link_libraries(test-encode-decode PRIVATE fdk-aac::fdk-aac)
target_include_directories(test-encode-decode PRIVATE upstream-test "${FDK_INC}/fdk-aac")
if(NOT MSVC)
  target_link_libraries(test-encode-decode PRIVATE m)
  target_compile_options(test-encode-decode PRIVATE -Wall -Wextra -O2)
endif()
