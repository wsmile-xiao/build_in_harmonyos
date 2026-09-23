# ckon 0.7.1 适配笔记

## 编译环境
- 构建系统: autotools（发布 tarball 无预生成 configure，需 autoreconf -fi）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: built

## 依赖（W0 已核验二进制在库）

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.84.0 | filesystem/regex/program_options；system 自 1.69 起 header-only |
| curl | 8.15.0 | 经 curl-config 提供编译/链接参数 |

## 编译步骤

1. 补丁：去掉 `configure.ac` 的 `AX_BOOST_SYSTEM` 与 `Makefile.am` 的 `ckon_LDADD += $(BOOST_SYSTEM_LIB)`（boost>=1.69 已无该库，AX_BOOST_SYSTEM 的无条件探测必然失败）。
2. `autoreconf -fi` 生成 configure。
3. `CONFIG_SHELL/SHELL` 指向能力探测通过的系统 shell 后执行 `./configure --prefix=<pkg> --with-boost=<boost> --with-curl-prefix=<curl> --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`，`make -j1`。
4. `make install` 安装 `bin/ckon`。

## 上游测试统计

| 口径 | 数值 |
|------|------|
| 上游自动化测试数 | 0 |

说明：上游 `test/` 目录仅含 `clone_testdir.sh`（git clone BesCocktail 仓库后人工运行的集成演示）、`ckon.cfg`、`ckonignore`，无自动判定 harness，不计入自动化测试数。消费者测试（test_package/test.sh）断言 `ckon --version` 输出版本串、`ckon --help` 输出工具描述（真实走 boost::program_options 解析），2 项断言。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | zlib/1.3.1.1 与 zlib/1.3.1 图冲突 | curl 锁 1.3.1，openssl/3.5.6.1 需 1.3.1.1（制品仓修复版） | `requires("zlib/1.3.1.1", override=True)`（gnustep-gui 先例） |
| 2 | configure 报 `working directory cannot be determined` | profile [buildenv] 将 CONFIG_SHELL 钉在 HNP bash，其在 HMDFS 路径 getcwd 间歇失败（E386） | 能力探测（实跑 `cd <HMDFS> && pwd` 且 stderr 为空）选定 shell 后，以内联 env 前缀执行 configure；conanbuild.sh 的 source 顺序决定工具链 env 会被 profile buildenv 覆盖，内联前缀是唯一可靠覆盖点 |
| 3 | config.guess 报 `can't create dummy.c: Permission denied` → `cannot guess build type` | config.guess 编译探针写 $TMPDIR 被 HMDFS 间歇拒绝 | 显式传 `--build/--host=aarch64-unknown-linux-ohos` 跳过探针 |
| 4 | 探测 shell 时全部候选被跳过 | HMDFS 上 `os.access(X_OK)` 恒 False（E524） | 改用 `os.path.isfile` 存在性判断 |

## 源码修改

| 文件 | 内容 |
|------|------|
| patches/0001-Makefile.am.patch | 删除 `ckon_LDADD += $(BOOST_SYSTEM_LIB)` |
| patches/0002-configure.ac.patch | 删除 `AX_BOOST_SYSTEM` 宏调用 |

## 版本串说明

`configure.ac` 的 `AC_INIT([ckon],[0.7])` 未随 v0.7.1 tag 更新，`ckon --version` 打印 `0.7`；配方/任务/目录版本为 0.7.1，以 tag 为准（消费者测试按 `0.7*` 前缀断言）。

## 注意事项

- `installCkon`/`cleanup.sh`/`autogen.sh` 为上游辅助脚本，包内仅交付 `bin/ckon`。
- ckon 运行时按 `ckon.cfg` 驱动 CMake 构建 ROOT 项目；无 ROOT 的环境仅验证到选项解析与帮助输出，完整 ROOT 项目流程不在本包验证范围。
---

**编译结束**: 2026-09-11 03:00
**最终状态**: built
