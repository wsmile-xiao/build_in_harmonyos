# ndiff 2.00 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-09-07
- 编译器: clang/clang++
- 状态: built

## 编译步骤

ndiff 2.00 是小型 C 命令行工具。任务平台显示版本 `2`，但 Conan 2.29.1
实测拒绝 bare integer version `2`，因此本归档和 Conan 引用使用上游真实版本
`ndiff/2.00`。上游默认可构建 native long-double precision 版本，未启用可选
GMP 依赖。

1. 配置:
   ```bash
   ./configure --prefix=<package>
   ```
2. 构建:
   ```bash
   make -j1 LN=cp
   ```
3. 上游测试:
   ```bash
   make -j1 check TMPDIR=<build_folder>/check-tmp LN=cp
   ```
4. 安装:
   `package()` 直接复制 `ndiff`、`ndiff-2.00` 和 `ndiff.1` 到 Conan 包目录。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 `make check` 默认使用 `/tmp/ndiff` | OHOS PC 上 `/tmp` 为只读文件系统 | 在 recipe 中传入 `TMPDIR=<build_folder>/check-tmp` |
| 2 | `make check` 创建临时 `ndiff-2.00` 时硬链接失败 | HMDFS 不允许 `ln` 创建硬链接 | 在构建、测试阶段传入 `LN=cp` |
| 3 | 官方源码主分发地址是 FTP | Conan HTTP downloader 不适合直接使用 `ftp://` | 使用公开 HTTPS 镜像 URL，并确认解包后的源码树与官方 FTP tarball 一致 |
| 4 | `--without-gmp` 仍导致 `gmp.h` 缺失 | 旧 configure 脚本只要看到 `--with/--without-gmp` 就把 `fp_package` 设为 gmp | 不传 GMP 相关参数，使用默认 native long-double precision |
| 5 | `make install DESTDIR=<package>` 仍写入 `//bin`/`//share` | 上游手写 Makefile 不支持 `DESTDIR`，且 `install` 目标并行时 `install-show` 可能抢跑 | 在 `package()` 中手动复制已构建二进制和 man 页到 Conan 包目录 |

## 源码修改

无源码补丁。

## 依赖版本

无第三方 Conan 依赖。可选 GMP 未启用。

## 验证结果

```bash
$ make -j1 check TMPDIR=$TMPDIR/ndiff-check2 LN=cp
This version of ndiff has been built with native long-double-precision arithmetic.
============ check001: ndiff -?
...
============ check026: ndiff --www
```

`test_package` 还会从消费者视角运行安装后的 `ndiff --version`，并验证数值容差内
比较返回成功、容差外比较返回差异报告。

## 注意事项

- 官方上游版本号为 `2.00`，平台任务版本显示为 `2`；Conan recipe 使用
  `version = "2.00"`，README/notes 中记录该差异。
- 官方 FTP tarball 的 MD5 为 `885548b4dc26e72c5455bebb5ba6c16d`，其解包源码树
  与 recipe 使用的 HTTPS 镜像包一致；recipe sha256 对应 HTTPS 镜像 tarball。
---

**编译结束**: 2026-09-08 08:12
**最终状态**: built
