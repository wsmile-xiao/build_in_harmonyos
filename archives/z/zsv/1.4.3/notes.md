# zsv 1.4.3 — HarmonyOS PC 适配笔记

## 版本纠正（重要）

- 任务早期曾出现 **zsv 0.3.10** 的提法，经核验 **liquidaty/zsv 上游不存在 v0.3.10**，
  正式目标为 **v1.4.3**（GitHub tag `v1.4.3`）。
- 本归档及分支 `feat/zsv-1.4.3`、conan 元数据、知识草稿中均未混入 0.3.10。

## 源码信息

- 上游: https://github.com/liquidaty/zsv
- 官方 URL: https://github.com/liquidaty/zsv/archive/refs/tags/v1.4.3.tar.gz
- SHA256: `8372ec277b0cf56d02e3407e355208875fdfa174a3ed01e6ffb9a00fe440fc43`
- 许可证: MIT
- 本地探针源: 工作区外 `~/builds/zsv-1.4.3.{orig,work}`（编译探针目录，非交付物）

## 构建系统

zsv **不是 CMake 项目**，也不是 autotools 主项目；使用**自定义 configure + Makefile**：

```
./configure --prefix=...      # 生成 config.mk（CC/AR/RANLIB/NEON/内置 pcre2、jq 自动检测）
make -j1                      # src/ 构建 libzsv.a，app/ 构建 CLI 工具（24 个二进制）
make install DESTDIR=...      # 头文件 + libzsv.a + zsv 主二进制（install 不含 libzsvutil.a）
make -C app install-util-lib  # 单独生成 libzsvutil.a
```

- configure 为 musl 风格自定义脚本（`#!/bin/sh`），无 config.guess/config.sub 依赖；
  失败项 `memmem`/`tgetent` 检测属预期（OHOS 缺失），configure 自动设 `NO_MEMMEM=1`、`NO_TGETENT=1`。
- **NEON**：OHOS aarch64 下 configure 自动识别 `HAVE_NEON=1`（探针证据，勿重复探测）。
- 配方 conanfile.py 严格按 configure + Makefile 驱动，**未虚构 CMake 入口**。

## OHOS 关键适配点（探针证据）

1. **嵌套 tarball 的 config.guess（E007 模式）**：zsv make 阶段会解压
   `app/external/pcre2-pcre2-10.47.tar.gz`、`jq-1.6.tar.gz` 并运行其 autotools configure；
   其 config.guess 无法识别 `HarmonyOS`（报 `unable to guess system type`）。
   → 补丁 `0001`（pcre2）/ `0002`（jq）：在 case 分支加入
   `*:HarmonyOS:*:*)` → `echo ${MACHINE}-unknown-linux-ohos`。
   补丁目标是嵌套 tarball 内部文件，故 conanfile `build()` 先解压→打补丁→重打包。
2. **HMDFS umask 077 临时目录权限（E011 模式）**：config.guess 用 `umask 077 && mktemp -d`
   建临时目录，HMDFS 上后续写入 `dummy.c` 报 Permission denied。
   → `0001` 补丁同时将 `umask 077` 改为 `umask 022`；conanfile 亦在 configure 前 `umask 022`。
3. **/tmp 只读（E002）**：`/tmp` 挂载只读，`touch /tmp/x` 报 Read-only file system。
   → 测试/临时文件全部使用工作区 `tmp/` 目录（zsv 测试默认 `TMP_DIR=源码根/tmp`）。
4. **whoami/chown 缺失**：OHOS 无 `whoami`/`chown` 命令（`which` 为空）——测试脚本若调用需 shim；
   zsv 测试未强制依赖，未额外打补丁。
5. **Makefile DESTDIR staging 边界**：zsv 顶层 `make install DESTDIR=...` 会把
   `src/`（头文件+libzsv.a）与 `app/`（bin/zsv）装到 `$DESTDIR/{include,lib,bin}`；
   `libzsvutil.a` 走 `install-util-lib` 单独生成，配方在 install 后补拷。
   注意 `install` 目标会先写真实 `PREFIX`（configure 的 --prefix），配方用
   `--prefix=<build/stage>` 可写路径 + `DESTDIR=$package_folder` 隔离，避免污染系统目录。
6. **libcurl**：仅用于上游测试数据（worldcitiespop_mil.csv 等）下载，**不是核心库依赖**，
   配方 `requirements()` 为空（不伪造依赖）。
7. **jq / pcre2 / sqlite3**：均为 zsv **builtin** 组件（`config.mk`：
   `HAVE_PCRE2_8=1`、`PCRE2_8_PREFIX=builtin`、`JQ_PREFIX=` 空），随 zsv 一起编译进库/CLI，
   未声明为 Conan 运行时依赖（不伪造）。

## G2 网络 / 源码来源（本轮解决）

- 旧 conan-verify G2 失败原因为 GitHub tarball 下载/镜像超时。
- 本轮处理（未改动源码版本/URL/SHA256）：
  1. conandata.yml 保留**官方 URL** + 正确 SHA256（R39，CI 自动加镜像 fallback）；
  2. 官方 URL 实测可下载（curl -L 200，12.8MB）；本地已预置
     `core.sources:download_cache`（按内容 SHA256 键控的 sources 备份），
     `conan create` 直接命中缓存，不再依赖弱网。
- 结论：G2 网络问题已解决，未绕过校验。

## 上游测试统计（真实重跑，2026-08-15）

`make -C app test`（app/test/Makefile）32 个顶层测试目标，逐目标独立运行（每目标 75s 超时）：

| 结果 | 数量 | 目标 |
|------|------|------|
| 完整 PASSED | 28 | count、echo、count-pull、sql、2json、serialize、flatten、pretty、desc、stack、2db、2tsv、jq、compare、overwrite、blank-leading-rows、rm、mv、2json-help、flatten-2、flatten-dupcol、check、quoted-nonstandard、compare-redline、compare-redline-v2、vuln-cve-underflow、vuln-finish-cell-dl-oob、vuln-fast-nonstandard-oob |
| TIMEOUT | 2 | test-select、test-select-pull（内部 test-quotebuff-select 子测试在 OHOS 挂起；此前 25/19 个断言通过） |
| 部分失败 / unrunnable | 1 | test-parallel（1/2 子测试通过；3+ 因 git apply 路径假设失败，顶层 Error 2） |
| NO-RESULT | 1 | test-paste（上游 TO-DO 占位，rc=0 无断言） |

- 合计断言 Passed 行：195（含 TIMEOUT 目标中已通过的 44 行）；Failed：0；Skipped：0。
- 统计口径：**test-quotebuff-select 与 test-parallel-3+ 均为顶层目标内部的子测试**，分别计入
  test-select/test-select-pull 的 TIMEOUT 与 test-parallel 的部分失败，不重复计数为独立目标。
- **test-parallel-3+**：上游测试假设 git 仓库上下文（`git apply chunk_break.diff` 及
  worldcitiespop_mil.csv 数据路径），tarball 解压环境下无法运行，如实记录为 unrunnable，
  **未修改上游断言/skip 条件/测试数据**，未将失败或未运行写成通过。

## 归档内容

- conanfile.py（custom configure + Makefile 配方）
- conandata.yml（官方 URL + SHA256 + patches 声明）
- test_package/（conanfile.py + MANIFEST.yml + test.sh：zsv version/count 冒烟）
- patches/0001-pcre2-config-guess-ohos.patch、0002-jq-config-guess-ohos.patch、
  0003-pcre2-config-sub-ohos.patch、0004-jq-config-sub-ohos.patch（共 4 个）
- manifest.yaml（status: built）
- reports/test-report.md

## 状态

- status: **built**（conan-verify 通过，未 publish/upload）
- E322 知识草稿：仍为 draft（内容为 qsb/Qt6，与本包无关，本轮未 promote）

## git diff --check 补丁空白说明（已核实，2026-08-16）

- `git diff --check` 对 patches/0001-0004 报 space-before-tab / trailing-whitespace 告警（共 35 行）。
- **性质**：全部来自补丁**上下文行保留上游 config.guess/config.sub 的 tab 缩进与空行字节**——这些行是
  patch 应用（上下文匹配）的必要内容，删除/改写会导致补丁无法应用。属上游字节保留，非本包引入缺陷。
- **已核实结论**：仓库补丁规范无该检查的正式豁免条款，但 CI/pre-commit 均无 whitespace 门禁；
  仓库已合入的同类补丁（abook/acpid 的 config.guess/config.sub 补丁）在同等检查下同样触发。
- **处理**：不修改补丁字节（保持 patch 可应用性与上游一致性）；本项不表述为 CI 通过项；
  W4/pre_pr_audit 审计（P0=P1=P2=P3=0）已覆盖该文件并判定不阻塞。
---

**编译结束**: 2026-08-16 09:29
**最终状态**: built
