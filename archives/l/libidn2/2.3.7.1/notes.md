# libidn2 2.3.7.1 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出 libidn2.so 等 1 个库，供链接与 dlopen。

## 关键适配

**未打任何补丁。** 上游源码直接可用鸿蒙 PC 原生工具链构建。

值得对照的是：仓内手工构建时代的 `libidn2/2.3.7` 打了 **16 个补丁**
（config.guess/config.sub 的 HarmonyOS 识别、doc/examples/po 等一系列）。
本包一个都不需要 —— 大概率是 conan 的 AutotoolsToolchain 把 `--build`/`--host`
三元组给全了，config.guess 那一类根本不会被触发。

## 版本号说明

版本取 **2.3.7.1** 而非 2.3.7：`archives/l/libidn2/2.3.7` 已是手工构建时代
**已发布**的条目（`status: published`，带 16 个补丁，`build_system: autoconf`）。
按仓内 repack 惯例（zlib 1.3.1→1.3.1.1、fftw 3.3.10→3.3.10.1、
poppler 25.12.0→25.12.0.2）另起版本号做 conan 化，**不改动那个既有条目**。
源码仍是上游 2.3.7。

## 选项取舍

- `--disable-doc` / `--disable-gtk-doc`：文档不进制品，设备上也没有 gtk-doc。
- `--disable-valgrind-tests`：上游自带测试不进制品，验收以本包 test_package 为准。

## 状态

built（真机 conan create + test_package 通过）
