# MLton

## 简介

MLton 是一个面向 Standard ML 的全程序优化编译器（whole-program optimizing compiler），以 SSA 中间表示为核心，通过深层内联、去盒化与单态化等全局优化生成接近手写 C 的高效原生代码。

## 功能概述

- 全程序优化：跨函数内联、数据流分析、去盒化（defunctorization / demultimodulization）、单态化等 SSA 优化管线
- 完整 Standard ML Basis Library 与 MLton 专属扩展库（basis-library/、lib/）
- 自带工具链：mllex（词法分析器生成器）、mlyacc（语法分析器生成器）、mlprof（性能剖析器）
- 自包含 runtime：生成的可执行文件内嵌 runtime，支持 PIE / 静态配置，运行期无外部运行时依赖
- 自带回归测试套件：make check 共 332 项（bin/regression 驱动）

## OHOS 适配

- **平台识别**：bin/platform、basis-library/mlton/platform.*、runtime/cenv.h 增加 HarmonyOS（ohos）识别，新增 runtime/platform/ohos.{c,h}；OHOS 复用经实际编译测试验证的 Linux-musl runtime 能力，MLton.Platform.OS.host 为 OHOS。
- **引导编译**：官方构建需先编译 bootstrap-polyml 引导编译器，配方以 Conan build_requires 引入 polyml/5.9.2.1（含 OHOS 平台支持与 ARM64 GC save-set 分配修复）。
- **TMPDIR**：OHOS /tmp 只读且不可靠，回归测试与 runtime 临时文件统一迁移到 TMPDIR。
- **filesys hardlink**：HMDFS 对 Posix.FileSys.link 返回 EPERM，hardlink 用例改由 /dev/shm 前缀承载。
- **real oracle**：OHOS musl libc atan2f 对 x<0 返回正确舍入，与上游 glibc golden 差 1 ULP，新增 regression/real.arm64-ohos.ok 平台 oracle 变体。
- **gzip**：OHOS /usr/bin/gzip 为 toybox 实现（仅支持短选项 [-19cdfkt]），安装脚本的 GNU 长选项改为 -f -9。
- **ELF 签名**：构建产物与打包 ELF 需用 HarmonyOS 签名工具自签名，签名后恢复原 mode 保留执行位。
- 与 Linux 的主要差异集中在工具链能力（toybox、签名工具）与文件系统（HMDFS /tmp、hardlink）层面；详细适配过程见版本级 20241230/notes.md。

## 依赖关系

- 编译依赖：gmp/6.3.0（Conan require）；polyml/5.9.2.1（Conan build_require，官方 bootstrap-polyml 引导编译器）
- 运行依赖：打包产物为自包含原生可执行文件，运行期依赖 musl libc 与动态链接器，无额外第三方运行时

## 参考资料

- 官网: https://www.mlton.org/
- 源码仓库: https://github.com/MLton/mlton
- 20241230 版本发布页: https://github.com/MLton/mlton/releases/tag/on-20241230-release
