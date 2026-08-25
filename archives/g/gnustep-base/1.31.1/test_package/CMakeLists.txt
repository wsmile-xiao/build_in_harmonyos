cmake_minimum_required(VERSION 3.20)
project(test_gnustep_base LANGUAGES C OBJC)

find_package(gnustep-base CONFIG REQUIRED)

add_executable(test_gnustep_base test_gnustep_base.m test_support.c)
target_compile_options(
  test_gnustep_base PRIVATE
  -fobjc-runtime=gcc
  -fblocks
  -fconstant-string-class=NSConstantString
)
target_link_options(test_gnustep_base PRIVATE -fobjc-runtime=gcc -fblocks)
target_link_libraries(test_gnustep_base PRIVATE gnustep-base::gnustep-base)
