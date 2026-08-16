# cddlib 0.94n 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出 libcddgmp.so 等 2 个库，供链接与 dlopen。

## 关键适配
- 删除 lib/*.la：其中烤死 libdir 绝对路径，会把下游 libtool 引到 //lib/ 死路
- 修 configure 的 umask 077→022（HMDFS E011）

## 状态
built —— 2026-08-16 在 HUAWEI MateBook（OHOS aarch64）真机验证通过。

真机 `conan create -pr ohos-native` 通过；test_package 断言单位正方形 H→V 的顶点数恒为 4（实得 4）。
