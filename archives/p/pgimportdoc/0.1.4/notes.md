# pgimportdoc 0.1.4 适配笔记

> **历史记录说明**：以下「编译环境」至「交付物」各节为 2026-06-12 手工流程（ohc-run 探索模式）的
> 历史记录，部分内容已过时——0001-configure.patch 已于 conan 适配（2026-08-08）删除；
> PostgreSQL 辅助源现为 18.1（见文末 conan 流程记录）；「状态: published」指当日本地部署，
> 当前权威状态以 manifest.yaml（built）为准。

## 编译环境
- 构建系统: makefile (PGXS - PostgreSQL Extension Build System)
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 状态: published（2026-06 手工流程本地部署状态，历史记录）

## 编译步骤

1. **初始化**: `ohc-run.py init-build pgimportdoc 0.1.4 --url=https://github.com/okbob/pgimportdoc/archive/refs/tags/0.1.4.tar.gz`
2. **补丁应用**: 添加 configure wrapper 脚本（PGXS项目无configure脚本）
3. **配置**: `./configure --prefix=$DEFAULT_PREFIX` (通过wrapper)
4. **编译**: `make` (使用 PGXS 构建系统，依赖 pg_config)
5. **安装**: `make install DESTDIR=$TEST_PREFIX` (staging隔离)
6. **部署**: `make install` (安装到 $DEFAULT_PREFIX)
7. **打包**: `ohc-run.py package pgimportdoc 0.1.4`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G0 clean verify failed (no configure) | PGXS项目无configure脚本 | 添加 0001-configure.patch，创建minimal configure wrapper |
| 2 | make install install-binPROGRAMs failed | PGXS install target差异 | 实际install成功（bin=1），只是部分make target不存在 |
| 3 | SSL证书下载失败 | 系统SSL证书问题 | 手动下载tarball后使用本地文件 |

## 源码修改

- **0001-configure.patch**: 添加minimal configure wrapper脚本（已于 2026-08-08 conan 适配时删除，当前无补丁）

## 依赖版本

- PostgreSQL 17.10（2026-06 手工流程，系统 pg_config；当前 conan 流程为 PostgreSQL 18.1 源码前端构建）
- libpq, libpgcommon, libpgport (PostgreSQL客户端库)

## 验证结果

```bash
$ pgimportdoc -V
pgimportdoc (PostgreSQL) 17.10
```
（2026-06 手工流程，基于系统 PostgreSQL 17.10；当前 conan 流程输出 `pgimportdoc (PostgreSQL) 18.1`）

## 交付物（2026-06 手工流程，ohc-run package 时代产物；当前 conan 流程交付由 CI 构建上传）

| 文件 | 大小 | 说明 |
|------|------|------|
| pgimportdoc-0.1.4-ohos-aarch64.tar.gz | 5202KB | 预编译包(aarch64) |
| pgimportdoc-0.1.4-ohos-aarch64-debug.tar.gz | - | 调试符号包(aarch64) |

## 注意事项

- PGXS项目依赖pg_config，需要已安装的PostgreSQL提供构建支持
- 编译产物pgimportdoc是PostgreSQL客户端工具，需要libpq运行时支持
- make check需要运行中的PostgreSQL服务器，在编译环境中不可用---

**编译结束**: 2026-08-08 01:30
**最终状态**: built
---

## CI 失败修复轮（2026-09-17，PR #4664 第 2 轮）

CI 失败（build #15845，[conan-build-test] 步骤）根因与修复：

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cd pgsrc/postgresql-18.1: No such file or directory` | `get(..., strip_root=True, destination=pgsrc)` 把 PG 源码内容直接解到 pgsrc/ 下（无子目录），随后 `cd pgsrc/postgresql-18.1` 失败 | `strip_root=False`，解压出 `pgsrc/postgresql-18.1/`；并在目录缺失时抛出明确异常 |
| 2 | 原 `make install -j1` 会构建并安装整个 PostgreSQL 服务端 | PG 顶层 install 递归全部子目录（含 backend） | 改为仅安装前端所需子目录：`make -C src/bin/pg_config install`、`src/include`、`src/port`、`src/common`、`src/interfaces/libpq`、`src install-local`（注意：不是 `install`，否则递归全树）、`src/makefiles install`、`config install`（PGXS 需要 install-sh/missing） |
| 3 | 二进制 RUNPATH 泄漏构建目录绝对路径（pginstall/lib） | PG configure 默认 `--enable-rpath`，把 $(libdir) 写进可执行文件 | configure 加 `--disable-rpath`，运行期由 conan（LD_LIBRARY_PATH）管理 |
| 4 | config.sub/config.guess 动态修复模式串与 PG 18 不匹配（静默 no-op） | PG 18 的 config.sub 结构已变（旧模式 `"\| linux-gnu* \| linux-dietlibc \| "` 不存在） | 改用 libpq/18.1 已验证补丁（0001/0002/0003）等价的锚点：config.sub 补 `ohos-linux)` 映射与 `ohos*` accept；config.guess 补 `__OHOS__` LIBC 探测与 `HarmonyOS)` 分支（锚点已逐一实测匹配 PG 18.1 源文件） |
| 5 | build() 每次生成无用的 configure wrapper 脚本 | 探索期遗留（PGXS 项目无 configure，conan 构建不调用它） | 删除；PG 源码树自带 configure，pgimportdoc 本身经 PGXS make 构建 |

关键验证结论（本地 conan create，ohos-aarch64 profile）：

- PG 18.1 tarball 不含预生成头文件（pg_*_d.h、gram.h 等），`make -C src/bin/pg_config install` 触发 submake-generated-headers → 用 perl(genbki.pl/gen_node_support.pl) + bison 生成——CI worker 已具备（libpq/18.1 同源构建已验证）
- PGXS 构建链：`make PG_CONFIG=<pginstall>/bin/pg_config` → pgxs.mk 自动 `NO_GENERATED_HEADERS=yes`（不再依赖 backend）
- 产物校验：PIE ✓ / NX(GNU_STACK RW) ✓ / Full RELRO(BIND_NOW) ✓ / 无 RUNPATH / NEEDED: libpq.so.5, libc.so
- test_package: `pgimportdoc --version` → `pgimportdoc (PostgreSQL) 18.1` ✓
- CI L2（直接执行二进制冒烟）为 skip 系已知平台限制：OHOS /system/bin/sh (mksh) 无法直接执行 ELF，
  build_and_test.sh 中 L2 设计为 non-blocking；真实冒烟由 test_package（bash 包装 + conanrun 环境）承担，L1=pass
---

**编译结束**: 2026-09-17 13:35
**最终状态**: built
