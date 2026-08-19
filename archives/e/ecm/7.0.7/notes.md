# ecm 7.0.7 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出 libecm.so 等 1 个库，供链接与 dlopen。

## 关键适配
- 删除 lib/*.la：其中烤死 libdir 绝对路径，会把下游 libtool 引到 //lib/ 死路
- 修 configure 的 umask 077→022（HMDFS E011）

## 状态
generated —— **recipe 已生成，真机尚未验证**。
跑通 `conan create <recipe> -pr ohos-native` 并确认 test_package 通过后，
把本行与 manifest.yaml 的 status 一并改成 built，并在下方补真机证据。
