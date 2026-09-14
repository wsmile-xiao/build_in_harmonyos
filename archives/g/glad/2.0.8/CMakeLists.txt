# CMakeLists.txt — glad 2.0.8（生成器产出的 C loader 静态库）
# 由 conanfile.py 导出到源码根；${GLAD_GEN_DIR} 由 CMakeToolchain 注入
# （build() 先运行官方生成器产出 generated/src/gl.c 与 generated/include）。
cmake_minimum_required(VERSION 3.15)
project(glad C)

if(NOT DEFINED GLAD_GEN_DIR)
  message(FATAL_ERROR "GLAD_GEN_DIR 未设置：需先运行 glad 生成器")
endif()

add_library(glad ${GLAD_GEN_DIR}/src/gl.c)
set_target_properties(glad PROPERTIES POSITION_INDEPENDENT_CODE ON)

target_include_directories(glad PUBLIC
  $<BUILD_INTERFACE:${GLAD_GEN_DIR}/include>
  $<INSTALL_INTERFACE:include>)

install(TARGETS glad
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib)
install(DIRECTORY ${GLAD_GEN_DIR}/include/ DESTINATION include)
