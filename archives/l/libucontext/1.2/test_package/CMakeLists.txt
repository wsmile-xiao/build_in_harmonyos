cmake_minimum_required(VERSION 3.15)
project(test_libucontext C)

find_package(libucontext REQUIRED)

add_executable(test_libucontext test.c)
target_link_libraries(test_libucontext PRIVATE libucontext::libucontext)

if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")
  add_executable(test_ohos_ucontext test_ohos_ucontext.c)
  target_link_libraries(test_ohos_ucontext PRIVATE libucontext::libucontext)
endif()
