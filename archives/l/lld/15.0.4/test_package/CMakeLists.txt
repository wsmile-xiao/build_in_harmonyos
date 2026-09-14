cmake_minimum_required(VERSION 3.15)
project(lld_consumer_test C)

if(NOT IS_ABSOLUTE "${LLD_EXECUTABLE}")
  message(FATAL_ERROR "LLD_EXECUTABLE must be absolute")
endif()
if(NOT EXISTS "${LLD_EXECUTABLE}")
  message(FATAL_ERROR "packaged ld.lld not found: ${LLD_EXECUTABLE}")
endif()
execute_process(
  COMMAND "${LLD_EXECUTABLE}" --version
  RESULT_VARIABLE LLD_RESULT
  OUTPUT_VARIABLE LLD_VERSION
  ERROR_VARIABLE LLD_ERROR
)
if(NOT LLD_RESULT EQUAL 0)
  message(FATAL_ERROR "ld.lld --version failed: ${LLD_ERROR}")
endif()
if(NOT LLD_VERSION MATCHES "LLD 15\\.0\\.4")
  message(FATAL_ERROR "unexpected ld.lld version: ${LLD_VERSION}")
endif()

add_executable(test_lld test_lld.c)
target_link_options(test_lld PRIVATE "-fuse-ld=${LLD_EXECUTABLE}")

# HarmonyOS AArch64-specific consumer test: the whole link step runs through
# the packaged ld.lld, and the produced executable verifies the 64-bit data
# model at runtime.
add_executable(test_ohos test_ohos.c)
target_link_options(test_ohos PRIVATE "-fuse-ld=${LLD_EXECUTABLE}")
