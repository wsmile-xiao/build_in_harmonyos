# libdecaf

> Ed448-Goldilocks / Curve25519 椭圆曲线密码库（Decaf 点压缩协议）

## 简介

libdecaf 是 Mike Hamburg 的 Ed448-Goldilocks 实现的发行版，实现了 Decaf
点压缩协议：在素数阶群上提供完备（无特殊分支/无定时泄漏）的椭圆曲线运算，
去除余因子。支持 Ed448-Goldilocks 与 Curve25519 两条曲线，提供 C 与 C++
两套 API，包括标量/点算术、Elligator 哈希到曲线、EdDSA 签名原语、
X448/X25519、SHAKE/SHA3 与 spongerng。上游以 MIT 许可发布，
官方分发渠道为 SourceForge 项目 ed448goldilocks。

## OHOS 适配要点

- CMake 4.x 兼容：上游 `cmake_minimum_required(VERSION 3.0)`，已补丁提升至
  3.5（patches/0001-cmake-min-version-3.5.patch）。
- aarch64 架构选择：上游 `if(${CMAKE_SYSTEM_PROCESSOR} MATCHES ...)` 在
  CMake 中展开后把值（如 aarch64）当作变量名重新求值，未定义恒假，导致
  aarch64 静默落到通用 arch_32 路径；补丁改为直接引用变量，配合配方注入的
  `CMAKE_SYSTEM_PROCESSOR=aarch64` 选择 arch_ref64 实现
  （patches/0002-fix-arm64-arch-detection.patch）。
- 严格警告关闭：上游 `ENABLE_STRICT` 默认开启 `-Werror`，新 clang 对生成
  的 C++ 头文件报 `-Wdeprecated-copy`，配方传 `-DENABLE_STRICT=OFF`。
- 构建期 Python：上游用 `FindPythonInterp` 运行 `src/generator/template.py`
  生成公共头文件（decaf.h、point_448.h 等），构建环境需提供 python3。
- 交叉 toolchain：配方按仓库惯例注入 `CMAKE_SYSTEM_NAME=HarmonyOS` 与
  `CMAKE_SYSTEM_PROCESSOR=aarch64`。

## 排除与替代

无（库目标完整构建，未排除组件）。上游测试程序（decaf_tester 等）仅在上游
`ENABLE_TESTS=ON` 时构建，不随包安装。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | - | 纯 C 实现，仅依赖 libc 与构建期 python3 |

## 功能验证

消费者测试（test_package）覆盖 decaf_448 标量算术、点算术（2G == G+G）、
编码/解码往返、点有效性与单位元拒绝：

```sh
conan create . --build=missing   # 自动运行 test_package
```

上游测试（设备原生 aarch64 实测）：ctest 2/2 通过（decaf 19 组全 PASS、
bench 冒烟），shakesum 摘要管道模式正常；详见本版本 notes.md。

## 参考

- [官方项目页](https://sourceforge.net/projects/ed448goldilocks/)
- [上游 git 仓库](https://sourceforge.net/p/ed448goldilocks/code/)
- [RFC 7748 (X448/X25519)](https://datatracker.ietf.org/doc/html/rfc7748)
- [RFC 8032 (Ed448/Ed25519)](https://datatracker.ietf.org/doc/html/rfc8032)
