# libisl 0.28 for HarmonyOS

## 概述

libisl（上游项目名 isl）在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。
整数集库，用于多面体模型的集合与关系运算，是 GCC/LLVM Polly 等编译器基础设施的依赖。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | libisl |
| 版本 | 0.28 |
| 下载地址 | https://libisl.sourceforge.io/isl-0.28.tar.xz |
| 官方文档 | https://libisl.sourceforge.io/manual.pdf |
| 依赖 | gmp/6.3.0 |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | autotools |

## 编译步骤

```bash
# 1. 下载源码
wget https://libisl.sourceforge.io/isl-0.28.tar.xz
tar -xf isl-0.28.tar.xz
cd isl-0.28

# 2. 应用补丁（如有）
patch -p1 < patches/0001-config.guess.patch
patch -p1 < patches/0002-config.sub.patch
patch -p1 < patches/0003-configure-tmpdir.patch

# 3. 配置
./configure --with-int=gmp --enable-portable-binary --with-gmp=system --with-gmp-prefix=<gmp prefix>

# 4. 编译
make -j1

# 5. 上游测试
make check -j1

# 6. 安装
make install
```

Conan 方式（推荐，CI 同款）：

```bash
conan create archives/l/libisl/0.28 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 补丁说明

| 补丁 | 目的 |
|------|------|
| 0001-config.guess.patch | `config.guess` 直接识别 HarmonyOS，返回 `*-unknown-linux-ohos` |
| 0002-config.sub.patch | `config.sub` 接受 `linux-ohos` 三元组 |
| 0003-configure-tmpdir.patch | `config.status` 临时目录走 `${TMPDIR:-.}` 并用 `umask 022` |

## 测试结果

上游 `make check`（默认 7 项：isl_test、codegen、pip、bound、isl_test_int、flow、schedule）
与 test_package（7 断言真实调用 isl C API）结果见版本目录 `notes.md`，
实测数字以 HMBS 真机预检日志为准。

## 参考资料

- https://libisl.sourceforge.io/
- conan-center `recipes/isl/all`
