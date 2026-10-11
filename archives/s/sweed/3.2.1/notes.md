# SweeD 3.2.1 适配笔记

## 编译环境
- 构建系统: makefile（上游多套 `Makefile*.gcc`；本配方用顺序版 `Makefile.gcc`）
- 编译日期: 2026-10-03
- 编译器: OHOS SDK clang（Conan profile 的 `tools.build:compiler_executables.c`）
- 状态: built

## 编译步骤

1. 取 Debian dfsg orig 源码包 `sweed_3.2.1+dfsg.orig.tar.xz`（上游仅网站发布、无 git tag）。
2. `build()` 执行 `make -f Makefile.gcc CC=<clang> CFLAGS="-Wall -O3" -j1`，编译
   `SweeD.c`、`SweeD_Input.c`、`SweeD_Kernel.c`、`SweeD_SFS.c`、`SweeD_CLR.c`、`SweeD_BFGS.c`，
   链接 `-lm`，产出 `SweeD`。
3. `package()` 安装 `bin/SweeD`、`licenses/README.txt`。
4. `test_package/test_sweed.sh` 运行 5 项检查。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 configure / 无通用 Makefile | 上游只提供 GCC 专用 `Makefile*.gcc` | 用顺序版 `make -f Makefile.gcc CC=<clang>`，`CC=` 覆盖文件内的 `CC = gcc` |
| 2 | 版本坐标 | 上游仅通过 Exelixis 网站发布、无 git tag | 用 Debian dfsg orig tarball（HTTPS）并固定 sha256 |

## 源码修改

无。零补丁。

## 依赖版本

无三方依赖（仅 libc 与 `-lm`）。

## 验证结果

```bash
# 消费者（test_package/test_sweed.sh，5 项）
SWEED_CHECK_SUMMARY checks=5 fails=0
```

## 注意事项

- 上游无测试套件，按 §3.6 口径声明上游 N=0，另加鸿蒙特有（消费者）测试 5 项。
- 本配方只构建顺序版；PTHREADS/MPFR/CHECKPOINTS 变体未使用。
