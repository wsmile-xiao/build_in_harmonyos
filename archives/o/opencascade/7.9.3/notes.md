# opencascade 7.9.3 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 libTKernel.so 等 45 个库，供链接与 dlopen。

## 关键适配
- package() 显式重签 ELF：链接后若再改字节（strip/抹 RUNPATH 等）链接期自签即失效，dlopen 报 Permission denied

## 状态
built（真机 conan create + test_package 通过）
