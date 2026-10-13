cmake_minimum_required(VERSION 3.16)
project(test_mesa C)

# mesa 26.1.5 (HarmonyOS PC) 消费者用例：
# 通过包提供的 EGL / GLESv2 头文件与库完成一次离屏渲染往返。
find_path(MESA_EGL_INCLUDE_DIR EGL/egl.h)
find_path(MESA_GLES2_INCLUDE_DIR GLES2/gl2.h)

find_library(MESA_EGL_LIB EGL)
find_library(MESA_GLES2_LIB GLESv2)

if(NOT MESA_EGL_LIB OR NOT MESA_GLES2_LIB)
  message(FATAL_ERROR "mesa test_package: libEGL/libGLESv2 not found in the package")
endif()
if(NOT MESA_EGL_INCLUDE_DIR OR NOT MESA_GLES2_INCLUDE_DIR)
  message(FATAL_ERROR "mesa test_package: EGL/GLES2 headers not found in the package")
endif()

add_executable(test_mesa test.c)
target_include_directories(test_mesa PRIVATE
  ${MESA_EGL_INCLUDE_DIR} ${MESA_GLES2_INCLUDE_DIR})
target_link_libraries(test_mesa PRIVATE ${MESA_EGL_LIB} ${MESA_GLES2_LIB} m)
