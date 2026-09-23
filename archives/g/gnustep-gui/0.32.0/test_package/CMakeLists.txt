cmake_minimum_required(VERSION 3.20)
project(test_gnustep_gui LANGUAGES C OBJC)

find_package(gnustep-gui CONFIG REQUIRED)

add_executable(test_gnustep_gui test_gnustep_gui.m test_support.c)
target_compile_options(
  test_gnustep_gui PRIVATE
  -fobjc-runtime=gcc
  -fblocks
  -fconstant-string-class=NSConstantString
)
target_link_options(test_gnustep_gui PRIVATE -fobjc-runtime=gcc -fblocks)
target_link_libraries(test_gnustep_gui PRIVATE gnustep-gui::gnustep-gui)
