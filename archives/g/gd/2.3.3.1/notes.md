# gd 2.3.3.1 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出 libgd.so 等 1 个库，供链接与 dlopen。

## 关键适配
- package() 显式重签 ELF：链接后若再改字节（strip/抹 RUNPATH 等）链接期自签即失效，dlopen 报 Permission denied
- 删除 lib/*.la：其中烤死 libdir 绝对路径，会把下游 libtool 引到 //lib/ 死路
- 修 configure 的 umask 077→022（HMDFS E011）

## 状态
built（真机 conan create + test_package 通过）
