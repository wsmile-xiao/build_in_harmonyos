# poco 1.15.3 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 libPocoNetSSL.so 等 16 个库，供链接与 dlopen。

## 关键适配
- package() 显式重签 ELF：链接后若再改字节（strip/抹 RUNPATH 等）链接期自签即失效，dlopen 报 Permission denied

## 状态
generated —— **recipe 已生成，真机尚未验证**。
跑通 `conan create <recipe> -pr ohos-native` 并确认 test_package 通过后，
把本行与 manifest.yaml 的 status 一并改成 built，并在下方补真机证据。
