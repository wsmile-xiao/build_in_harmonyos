cmake_minimum_required(VERSION 3.15)
project(pinocchio_test_package CXX)

# 为什么 test_package 必须走 CMake 而不是手写 clang++ 命令行：
#
# pinocchio 的 CMake config 导出了一批**必须的编译定义**，
# 手写命令行拿不到它们（conan 的 cpp_info 只带 include/lib 路径）：
#
#   BOOST_MPL_LIMIT_LIST_SIZE=30        ← 默认上限 20，不够 pinocchio 用
#   BOOST_MPL_LIMIT_VECTOR_SIZE=30
#   BOOST_MPL_CFG_NO_PREPROCESSED_HEADERS  ← 不设则上面两个 LIMIT 不生效
#   BOOST_FUSION_INVOKE_MAX_ARITY=12
#   PINOCCHIO_ENABLE_TEMPLATE_INSTANTIATION
#   PINOCCHIO_WITH_COLLISION / _WITH_URDFDOM / _WITH_HPP_FCL
#   PINOCCHIO_URDFDOM_HEADERS_{MAJOR,MINOR,PATCH}_VERSION
#
# 缺了它们的实际报错（真机实测，逐条对得上）：
#   · too many template arguments for class template 'list'      ← LIMIT_LIST_SIZE
#   · no member named 'apply' in ...mpl::non_sequence_tag        ← 同上
#   · using declaration refers into 'Base::', which is not a base class
#                                                                ← ENABLE_TEMPLATE_INSTANTIATION
#
# 两点要分清：
#   ① conan 的 CMakeDeps 是按**配方的 cpp_info** 生成 config 的，
#      **不会**自动继承上游安装的那份 CMake config。
#      所以这些定义必须由配方在 `package_info()` 里写进 `cpp_info.defines`，
#      否则不只本测试，**任何消费方都拿不到、都编不过**——那是包本身的缺陷。
#   ② 本文件用 find_package + target_link_libraries 消费，
#      定义/include/传递依赖由 CMake 自动施加，不必在编译命令行里手抄。

# ohos.toolchain.cmake 把 CMAKE_FIND_ROOT_PATH_MODE_* 设成 ONLY（只在 sysroot 里找），
# 于是 find_package 看不见 CMakeDeps 生成在 generators/ 下的 pinocchio-config.cmake，
# 报 "Could not find a package configuration file provided by pinocchio"。
# 这里放开成 BOTH —— 本文件在 toolchain 之后执行，故盖得住它。
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)

find_package(pinocchio REQUIRED CONFIG)
# 显式再找一次 boost：pinocchio 的公开头直接 #include <boost/next_prior.hpp> 等，
# 实测只 link pinocchio::pinocchio 时 boost 的 include **没有**传递过来
# （boost 包里确实有 next_prior.hpp，探测过；是传递链断了，不是 boost 缺头）。
find_package(boost REQUIRED CONFIG)

add_executable(test_probe test.cpp)
target_link_libraries(test_probe PRIVATE pinocchio::pinocchio boost::boost)

# 诊断：把实际生效的 include 路径打出来，省得下一轮还要靠猜
get_target_property(_pin_inc pinocchio::pinocchio INTERFACE_INCLUDE_DIRECTORIES)
message(STATUS "pinocchio INTERFACE_INCLUDE_DIRECTORIES = ${_pin_inc}")
get_target_property(_pin_link pinocchio::pinocchio INTERFACE_LINK_LIBRARIES)
message(STATUS "pinocchio INTERFACE_LINK_LIBRARIES = ${_pin_link}")
