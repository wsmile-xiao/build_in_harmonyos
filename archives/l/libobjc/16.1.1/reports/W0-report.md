# W0 report: libobjc 16.1.1

- Issue: 待补（本机前置适配，任务清单未提供明确 issue 编号）
- Date: 2026-09-11
- Dependency role: GNU Objective-C runtime，无独立上游，从 GCC 16 源码树构建 libobjc 子库。

## 上游信息

- 软件：libobjc（GNU Objective-C runtime，GCC 内置 runtime 库）。
- 上游：https://gcc.gnu.org/ ，源码位于 GCC 源码树 `libobjc/` 子目录。
- 许可证：GPL-3.0-or-later WITH GCC-exception-3.1（runtime 例外，链接不传染）。
- 版本映射：Conan 16.1.1 → 上游 GCC 16.1.0（GCC 官方 ftp 无 gcc-16.1.1.tar.xz，
  仅 16.1.0 / 16.2.0；16.1.1 为 releases/gcc-16 分支点，采用同系列官方 tarball 保证可复现）。
- 源码 tarball：gcc-16.1.0.tar.xz，sha256 `50efb4d94c3397aff3b0d61a5abd748b4dd31d9d3f2ab7be05b171d36a510f79`
  （本机下载复核，sha512 与官方 buildroot 记录一致）。

## 依赖

- 构建期 in-tree 依赖（GCC download_prerequisites 选定，已校验 sha256）：
  - GMP 6.3.0
  - MPFR 4.2.2
  - MPC 1.3.1
- 编译工具链：clang + clang++（GCC 16 前端为 C++ 实现）、GNU as/ld（设备
  `/data/service/hnp/bin/`）、bash、make、binary-sign-tool（OHOS ELF 签名）。
- ISL：可选，已 `--without-isl` 关闭。
- gettext：NLS 关闭后无需。
- 无额外 Conan 依赖。

## 依赖数量与结论

```text
依赖数量：3 个 in-tree 构建源（gmp/mpfr/mpc）
已满足依赖：全部 bundled 进配方，无缺失
缺失依赖：无
是否需要拆分依赖适配：否（gmp/mpfr/mpc 是 GCC 官方 in-tree 构建源，非独立 Conan 包）
阻塞点：无前置阻塞；真机 shadow CI 需排队
下一步：本机前置验证 -> 真机 shadow CI（单包排队）
```

## Source and build system

- 源码：GNU GCC 16.1.0 release archive（tar.xz，98MB）。
- 构建系统：GCC 顶层 autotools（configure + make），native aarch64-linux-ohos。
- 构建目标：c+objc 前端 + target libgcc + target libobjc。
- 上游测试：objc.dg（DejaGNU），需 DejaGNU 环境，OHOS 隔离 job 不现实，改为
  test_package 消费者验证。

## Decision

前置适配完成，等待真机空闲窗口后执行隔离 job 的 shadow CI。
