# fmt 8.1.1 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 libfmt.so 等 1 个库，供链接与 dlopen。

## 关键适配
- 无特殊适配：上游源码直接可用鸿蒙 PC 原生工具链构建。

## 状态
built（真机 conan create + test_package 通过）
