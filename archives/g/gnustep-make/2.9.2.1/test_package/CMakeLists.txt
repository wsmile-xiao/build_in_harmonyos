cmake_minimum_required(VERSION 3.20)
project(test_gnustep_make LANGUAGES C OBJC)

find_package(gnustep-base CONFIG REQUIRED)

# 上游 GNUstep TestFramework 的 9 个 example（来自 gnustep/tools-make
# make-2_9_2 的 TestFramework/，example1-9.m 原样保留，未做任何修改）。
# 依赖 Foundation（gnustep-base）与 libobjc2（通过 gnustep-base::gnustep-base 传递）。
set(EXAMPLES example1 example2 example3 example4 example5 example6 example7 example8 example9)
foreach(EX ${EXAMPLES})
  add_executable(${EX} testing/${EX}.m)
  target_compile_options(${EX} PRIVATE
    -fobjc-runtime=gcc
    -fblocks
    -fconstant-string-class=NSConstantString
  )
  target_link_options(${EX} PRIVATE -fobjc-runtime=gcc -fblocks)
  target_link_libraries(${EX} PRIVATE gnustep-base::gnustep-base)
endforeach()

# 鸿蒙特有测试：验证 gnustep-make 针对 HarmonyOS PC 的适配配置
# （NSConstantString / gnustep-2.0 ABI / -O0 / ng-gnu-gnu / IS_LINUX=.so）
add_executable(test_ohos_config test_ohos_config.c)
