# tachyon 0.99.5 编译笔记（HarmonyOS PC · 手写 Makefile）

## 定位
- 产 1 个命令行程序 `bin/tachyon`（并行光线追踪渲染器），**无库无头**。
- 直接消费方：`passagemath-tachyon` 的 wheel —— 它把 `bin/tachyon` 塞进
  wheel 的 `sage_wheels/bin/`，`sage.interfaces.tachyon` 起子进程调它。

## 关键适配
- **原始 tarball 没有 aarch64 目标**：`unix/Make-arch` 里只有 x86/ppc/ia64 等，
  aarch64 的 `linux-arm-thr` 由 sage/passagemath 的补丁补上。本 recipe 沿用同一份
  （`patches/0001-make-arch-linux-arm-thr.patch`），与上游 wheel 的构建方式一致。
- **CC/AR/RANLIB/STRIP 必须显式给**：`linux-arm-thr` 这个目标不设 CC，
  会落到 make 内置默认 `cc`，设备上没有该名字的工具。
- **`strip` 跑在链接之后**（`unix/Makefile:169`），会把链接器刚打上的自签改废
  → `package()` 必须重签，不能沿用"靠链接器自签"那条默认路径。
- **PNG 支持是静默可选的**：`-format PNG` 分支被 `#if defined(USEPNG)` 包着；
  libpng 没接上时 tachyon 不报错，只打印一行 "Unknown/Unsupported Image Format"
  然后回退成 Targa。故 test_package 断言的是**产物真是 PNG 且 IHDR 尺寸正确**，
  这才能把"PNG 支持没编进去"这种静默退化逼出来。
- 只 `make <arch 目标>`（= libtachyon.a + libmgf + tachyon），不碰 OptiX/OpenGL demo。

## 状态
built —— 2026-08-16 在 HUAWEI MateBook（OHOS aarch64）真机验证通过。

真机 `conan create -pr ohos-native` 通过；test_package 渲染出 64x64 PNG（691 字节，IHDR 尺寸对账），证明 libpng 真的链上了。
