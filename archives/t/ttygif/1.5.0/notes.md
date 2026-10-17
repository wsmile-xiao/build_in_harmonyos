# ttygif 1.5.0 — HarmonyOS PC 适配笔记

- 上游: https://github.com/icholy/ttygif （tag `1.5.0`，纯 C，4 个 .c + 4 个头，13 个文件）
- 取源: `https://codeload.github.com/icholy/ttygif/tar.gz/refs/tags/1.5.0`
  sha256 `b5cc9108b1add88c6175e3e001ad4615a628f93f2fffcb7da9e85a9ec7f23ef6`
- 构建系统: 裸 Makefile（M18 烧路径族：`CC = gcc` 裸赋值、`PREFIX ?= /usr/local` 可覆盖）
- 状态: built（本地 conan create 真实通过，未 upload）
- 依赖: 运行期外部工具 imagemagick/7.1.2.29（`requires(..., run=True)`），xwd 见「适用边界」

## 症状

1. 任何调用（含 `ttygif --version` / `--help`）在鸿蒙 PC 上未看任何参数即 fatal 退出：
   `Error: Failed to create tmp directory.`
2. 无头环境（无 `DISPLAY`/`WINDOWID`）下连 `--version` 都取不到——usage/version 判定排在
   WINDOWID 相关初始化之后，先崩在前面的初始化里。
3. `ttygif -v` 打印 `1.4.0`，与包版本 1.5.0 自相矛盾。

## 根因

1. `main()` 开头无条件 `mkdtemp("/tmp/ttygif.XXXXXX")`，而鸿蒙 PC 的 `/tmp` 挂在只读文件系统上
   （`touch /tmp/x` → `Read-only file system`，即知识条目 E002），mkdtemp 必然失败。
2. 上游把 `argc<2` 的 usage 与 `--help`/`--version` 判定放在 WINDOWID 探测之后；无头环境下
   `xgetwinid` 相关路径先行失败，版本分支永远到不了。
3. 上游 tag 1.5.0 的 Makefile 里 `VERSION = '"1.4.0"'`（-v 打印的就是这个宏），上游发版时忘了同步。

## 最小复现

```sh
CC=clang make -j1 CC=clang          # 或 conan create 全流程
./ttygif --version                  # → Error: Failed to create tmp directory.（退出码非 0）
```

## 已试过的失败方案（防重复踩）

1. **`refs/tags/v1.5.0`**：HTTP 404——上游 tag 不带 `v` 前缀，必须用 `refs/tags/1.5.0`。
2. **Debian 池 URL**（`deb.debian.org/.../ttygif_1.5.0.orig.tar.gz`）：sha256 与上游逐字节一致，
   但 PF7 把 Debian 池判为下游重打包源一律拦截 ⇒ 只用于 sha256 交叉校验，不写进 conandata/manifest。
3. **命令行覆盖 `CFLAGS`**：Makefile 的 `CFLAGS +=` 遇命令行赋值会整体丢弃自加部分，连带丢
   `-DVERSION` ⇒ 只覆盖 `CC`（`CC = gcc` 是裸赋值，只有 make 命令行赋值能覆盖），不动 CFLAGS。
4. **为 `UNAME := $(shell uname)` 打补丁**：假雷。本机 `uname` 返回 `HarmonyOS`，两个 ifeq 双双不
   命中，但全树 grep `OS_LINUX` 命中 0 次（只有 3 处 `#ifdef OS_DARWIN`）⇒ 默认编译路径就是
   Linux 行为。**不要为它打补丁、不要加 `-DOS_LINUX`、不要据此判平台不兼容**。
5. **指望 `requires(..., run=True)` 自动带上 imagemagick 的 bin/**：已发布的 imagemagick 配方只
   声明 components、`cpp_info.bindirs` 为空 ⇒ conanrun 环境里只有 libpng 的 bindir，`convert`
   不可达（实测 conanrun.sh）。⇒ 消费端须按依赖包目录显式解析（test_package 的 `_bin_dir`）。
6. **给 xwd 建包/打补丁来补全抓屏链**：`archives/x/xwd/1.0.9` 只有 manifest/notes/patches、无
   conanfile.py，`conan download xwd --only-recipe -r=ohpcd` 报 `Recipe 'xwd' not found` ⇒
   R36/PF4 禁止在本 PR 捎带补依赖（详见「适用边界」）。
7. **框架的 `ci/tools/extract_upstream_tests.sh`**：硬编码 `/tmp` 工作目录，在本平台必然失败
   ⇒ 改用手工等价扫描（证据 `reports/upstream-test-scan.txt`）。

## 最终方案

1. **补丁 0001（portability）**：① 帧暂存目录模板不再硬编码 `/tmp`，优先取 `TMPDIR`，未设置或
   为空时回落 `/tmp`（E002 正解；回落分支保持上游原语义，Linux/macOS 不受影响）；②
   `argc<2` 的 usage 与 `--help`/`--version` 判定上移到一切显示相关初始化之前，无头环境下版本
   号可稳定读取（CI 的 L2 冒烟探针依赖此读数）。
2. **补丁 0002（bugfix）**：Makefile `VERSION` 由遗留的 `1.4.0` 更正为与 tag 一致的 `1.5.0`。
3. **取源**：conandata 用官方 codeload 端点；URL 末段是裸 tag 名（无 `.tar.gz` 扩展名）⇒
   `conanfile.source()` 必须 `self.get(..., filename=...)` 显式传文件名，否则 conan 按末段猜
   压缩格式会选错解码器（`archives/v/vamps/0.99.2` 同型坑）。
4. **运行期工具面**：`requires("imagemagick/7.1.2.29", headers=False, libs=False, run=True)`——
   只有 `run=True` 的 requires 才进 conanrun 环境（`tool_requires`/`run=False` 都不进，E365/E442，
   presage 三轮 CI 实证）；imagemagick 的 bin 目录在消费端按 `package_folder` 显式解析，不把
   其他包的绝对缓存路径写进本包 env_info。
5. **测试面**：上游 0 测试（清点证据 `reports/upstream-test-scan.txt`：13 个文件无测试目录、
   `make -np` 无 check 目标、六类标记仅命中许可证文案与 2 处 libc assert）。test_package 自加
   51 条消费者断言（真执行打包二进制）：账本不变式 `DISCOVERED = PASS + FAIL + SKIP` 由脚本
   末尾自检行实测；产物一律写按进程号分址的 scratch 目录（框架 L1e 会起第二次 conan test）；
   脚本零命令替换零反引号（toybox sh 的 `$(…)` 会往只读 /tmp 落临时件）。

## 适用边界

1. **E01 端到端抓屏→GIF 腿按实测依据 skip**：ttygif 运行期 exec `xwd`（X11 抓屏）与 `convert`
   （GIF 合成）。`convert` 经 `requires(run=True)` + 显式 bindir 解析可达；`xwd` 在本仓不是 conan
   包（见失败方案 6）且测试环境 `DISPLAY` 为空 ⇒ X11 抓屏路径无输入源。该腿记为**未执行项**
   （带一手取证），不伪造 GIF 断言、不放宽断言凑绿。`convert` 编解码能力面（PNG/XWD coder
   缺位）由 D 组用 `identify -list format` 实测后按依据 skip。
2. **不做实时抓取**：本包是 ttyrec 文件→GIF 转换器；SCT 台账所称 openpty/termios 抓取面经复测
   不存在（openpty/posix_openpt/forkpty 全 0 处，termios 仅 tcgetattr(0) 读终端状态）。
3. **`PREFIX ?= /usr/local` 可覆盖**，配方走 conan 前缀；包是纯应用（bin/ttygif），无库产物，
   不涉系统同名库隔离（R26）。
4. 补丁均为 POSIX 可移植性/上游笔误修正，新增行不含平台宏（R8/PF5）。

## 测试数字口径

- 上游测试: 0（`upstream_tests_exist: false`，清点证据 `reports/upstream-test-scan.txt`）
- 新增消费者断言: 51 条（test_package/test.sh，真执行打包二进制）
- 彩排实测（2026-09-25，主理-48）: discovered=51 pass=49 fail=0 skip=2
  （E01 端到端按 DISPLAY 空 + xwd 配方缺席实证 skip；图像编解码链按 identify 实测 skip）
- 正式门禁读数以本次 conan-verify / CI 判决为准，PR 正文数字与之一致。
---

**编译结束**: 2026-09-26 02:19
**最终状态**: built
