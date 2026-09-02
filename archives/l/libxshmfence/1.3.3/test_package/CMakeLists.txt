cmake_minimum_required(VERSION 3.20)
project(libxshmfence_test_package C)

include(CTest)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

# xshmfence.h is self-contained (only includes X11/Xfuncproto.h from
# xorgproto), so the consumer needs nothing beyond the libxshmfence package.
find_package(libxshmfence CONFIG REQUIRED)

add_executable(libxshmfence_api_surface api_surface.c)
target_link_libraries(libxshmfence_api_surface PRIVATE libxshmfence::libxshmfence)
target_compile_options(libxshmfence_api_surface PRIVATE -Werror)
add_test(NAME libxshmfence_api_surface COMMAND libxshmfence_api_surface)

add_executable(libxshmfence_version_contract version_contract.c)
target_link_libraries(libxshmfence_version_contract PRIVATE libxshmfence::libxshmfence)
target_compile_options(libxshmfence_version_contract PRIVATE -Werror)
add_test(NAME libxshmfence_version_contract COMMAND libxshmfence_version_contract)

# 上游唯一自动化测试（test/xshmfence_test.c，未修改）：fork 5 个子进程
# 共享映射同一 xshmfence，busy-wait + alarm(10) 时序保护，父进程 trigger
# NCHECK=10 轮，全部通过返回 0。头文件按上游相对路径 vendored
# （upstream_test/xshmfence.h，来自上游 src/xshmfence.h），库用已安装的
# libxshmfence::libxshmfence。上游源码无 -Werror，保持默认编译。
add_executable(libxshmfence_upstream_test upstream_test/xshmfence_test.c)
target_include_directories(libxshmfence_upstream_test PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/upstream_test)
target_link_libraries(libxshmfence_upstream_test PRIVATE libxshmfence::libxshmfence)
add_test(NAME libxshmfence_upstream_test COMMAND libxshmfence_upstream_test)
