# cdck

## 简介

cdck 是一个检测 CD/DVD 光盘质量的命令行工具。即使光盘上所有文件都可读，个别扇区的不良读取计时也可能预示未来不可读；cdck 按扇区读取整盘并记录计时，给出质量结论，还可输出 gnuplot 可用的计时表。

## 版本信息

- **当前版本**: 0.7.0
- **作者**: Alexey Semenoff
- **官网**: http://swaj.net/unix/index.html#cdck

## 功能特性

1. **光盘质量检测**: 按扇区读取计时，定位读取缓慢/不可读扇区
2. **光盘信息输出**: 默认 `-i` 模式打印 TOC 与文件系统判断，不做计时
3. **gnuplot 数据**: `-p/-o` 输出计时数据文件，可绘图分析
4. **零外部依赖**: 仅使用 libc 与 `linux/cdrom.h` ioctl，无第三方库

## 编译说明

### 编译要求

- C/C++ 编译器（OHOS 使用 clang/clang++）
- make（Autotools 预生成 configure，无需 autoconf/automake）

### 构建系统

Autotools 工程：

```
./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
make -j1          # 含 src（cdck 二进制 + 内部 libcdck）与 man（需 pod2man，否则跳过）
make check        # 不存在！上游无 TESTS/check 目标，仅 automake 默认空目标
```

## OHOS 适配要点

- 2001 版 `config.sub` 不识别 aarch64 与 linux-ohos，补丁同步补充（aalib 同年代包先例）
- configure 强依赖 perl（gcc 版本探测）且硬编码 `gcc -print-file-name=libsupc++.a`；补丁使其缺 perl 可继续、SUPCXX 按 `$CC` 条件解析
- `CXXLINK` 由 `$(CC)` 改为 `$(CXX)`，clang 链接 C++ 程序才带 libc++ 运行时
- 发布包自带 maintainer 生成的 `src/config.h` 会遮蔽 configure 产物，`source()` 中删除
- man 页需 pod2man；缺失时预建最小 `cdck.1` 跳过文档构建，`package()` 只交付 `bin/cdck` 二进制
- 上游无任何测试（43 文件审计）；test_package 用 `-V` 版本、`-h` 帮助、坏设备 TOC 错误三条真实路径验证
