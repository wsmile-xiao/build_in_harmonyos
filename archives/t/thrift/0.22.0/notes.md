# thrift 0.22.0 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 libthrift.so 等 1 个库，供链接与 dlopen。

## 关键适配
- 无特殊适配：上游源码直接可用鸿蒙 PC 原生工具链构建。

## 状态
generated —— **recipe 已生成，真机尚未验证**。
跑通 `conan create <recipe> -pr ohos-native` 并确认 test_package 通过后，
把本行与 manifest.yaml 的 status 一并改成 built，并在下方补真机证据。
