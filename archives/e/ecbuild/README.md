# ecBuild

ECMWF 的 CMake 构建系统（纯 CMake 模块集，无库无头）

上游：https://github.com/ecmwf/ecbuild

## 鸿蒙 PC 适配要点

- 纯 CMake 模块包：无库无头，须用 cmake_build_modules 让下游 config 主动 include 上游入口
- 宏靠**重定义 project()** 注入，find_package(ecbuild) 必须写在 project() 之前
- project() 要求带 VERSION 参数，否则 ecbuild_critical
- OS 白名单不认 HarmonyOS：补丁让其按 linux 处理（Linux 内核 + musl，/proc 齐备）
