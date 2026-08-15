# libtpms 0.10.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-13
- 编译器: clang/clang++ 15.0.4
- 目标: aarch64-unknown-linux-ohos (OHOS arm64)
- 状态: built

## 编译步骤

1. 下载并校验上游标签源码 `v0.10.2`（SHA256 见 manifest.yaml）。
2. 在源码目录执行 `autoreconf --install --force` 生成 `configure`（标签源码不含预生成文件）。
3. `./configure --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos --with-openssl --with-tpm2`。
4. `make -j4` 编译静态库 `libtpms.a`。
5. `make check` 运行上游 10 项测试。
6. `make install` 安装到 Conan package 目录。
7. 消费者测试链接 `libtpms` 并调用 `TPMLIB_GetVersion()`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `autoreconf` 报 `pkgconfigdir`/`LIBTOOL` 未定义 | 环境缺 libtool/pkg-config 宏 | 通过 `build_requirements` 引入 automake/libtool 工具包 |
| 2 | HMDFS 下 `config.status` 因 umask 077 报 Permission denied | HarmonyOS 文件系统对 umask 目录兼容差异 | 配方内去除 configure 中 `umask 077` 目录创建逻辑 |
| 3 | `stat: Unknown option '%z'` | `tests/common` 将 HarmonyOS 误判为 OpenBSD | patch 0002：`get_filesize` 平台判断加入 HarmonyOS |
| 4 | `fuzz.sh` 首个语料即段错误 | Conan Release 注入 `-DNDEBUG`，编译掉测试里带副作用的 `assert(TPM_Malloc(...))`，导致 `memcpy(NULL)` | 配方 `generate()` 置 `tc.ndebug = None` |
| 5 | `NVMem.c` 编译报 unused `fseek` 结果（Clang 15 `-Werror`） | NDEBUG 下 `assert(irc == 0)` 消失 | 与 #4 同根因：配方置 `tc.ndebug = None` 禁用 NDEBUG |

## 源码修改

- `patches/0001-bootstrap-autotools-snapshot.patch`：为不含预生成 `configure` 的标签源码提供 G0 直配入口，并兼容 HMDFS 的临时目录创建（build）。
- `patches/0002-tests-support-harmonyos-stat.patch`：`tests/common` 的 `get_filesize` 平台判断加入 `HarmonyOS`（test）。

## 依赖版本

- openssl/3.5.6

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default -s:b os.version=6.0 --build=missing
# TOTAL: 10  PASS: 10  SKIP: 0  FAIL: 0  ERROR: 0
# test_package: TPMLIB_GetVersion() -> 0x00001002 (非零，通过)
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libtpms.a` | 静态库 |
| `include/libtpms/` | 公共头文件 |

## 注意事项

- 必须完整运行 `make check` 的全部 10 项测试（含 `object_size` 静态测试），不能只验证编译。
- 消费者测试必须真实调用 `TPMLIB_GetVersion()`，不能是空壳打印。
---

**编译结束**: 2026-08-14 15:39
**最终状态**: built
