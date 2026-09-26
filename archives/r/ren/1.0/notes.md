# ren 1.0 适配笔记

## 编译环境

- 构建系统：makefile（上游只有一个 8 行 Makefile，无 configure）
- 编译日期：2026-09-24
- 编译器：OHOS clang 15.0.4（`tools.build:compiler_executables`，profile `ci/conan/profiles/ohos-aarch64`）
- 本地运行器：x86_64 + qemu-aarch64 10.0.13（binfmt 已注册）
- 状态：built

## 源码与依赖

- 源码：`https://www.ibiblio.org/pub/Linux/utils/file/ren-1.0.tar.gz`（ibiblio Linux 软件档案，即
  sunsite/metalab 原始发布位置），8587 字节，sha256
  `6ccf51b473f07b2f463430015f2e956b63b1d9e1d8493a51f4ebd70f8a8136c9`。
- 归档内容共 6 个文件：`Makefile`、`README`、`ren.1`、`ren.c`、`ren.c.linux-patch`、
  `rename-files.orig`（1988 年 comp.sources.unix Vol.18 Issue 22 原始 shar）。
- 许可：归档内没有许可文本，只有 README 说明来源；配方 `license` 记为
  `LicenseRef-comp.sources.unix`。
- 依赖（W0）：无第三方依赖，只用 libc；配方没有 `requirements()`。
- 历史核验（W0b）：仓库中没有 ren 的历史归档；制品仓查询 `ren/1.0` 返回
  `system acceleration policy not enabled`（E477：CNB 对不存在的包返回此文本），确认是首次适配。
- 语言预检（R47）：`lang-preflight` 判定 c（make，1 个源文件，占比 100%），与任务 cpp 同族，继续适配。

## 上游测试清点（R51）

| 项目 | 结果 |
|---|---|
| `test/`、`tests/` 目录 | 0（归档只有上述 6 个文件） |
| Makefile 测试目标 | 无：只有 `all`、`ren`、`install`（仅 echo 一句提示）、`clean` |
| ctest / pytest / 测试脚本 | 0 |
| 上游用例数 N / 可运行 N′ / 通过 | 0 / 0 / 0（上游确无测试） |

补全测试：`test_package/test.sh` 按 `ren(1)` 描述的行为编写 13 个场景、53 条断言，直接运行
打包产物 `bin/ren`（AArch64 运行器直接执行，其他架构通过 qemu-aarch64 执行；找不到 qemu
时判失败，不会跳过）：

1. 参数个数错误打印 Usage 并退出 1；
2. `'*.txt' '#1.md'`：保留文件内容，不匹配文件与点文件不动，`-v` 输出两行重命名记录；
3. man page 例子 `'abc*.*.*' 'xyz#1.#3'`：`abc.txt.doc` → `xyz.doc`；
4. 路径前缀 + `'??' '#2#1'`：两文件互换（重命名环），经临时名 `renTMP*` 完成且无残留；
5. `'*' '#1a'`：链式重命名 `a → aa → aaa` 顺序正确，数据不丢；
6. 两个文件映射到同一新名：整体中止，一个都不改；
7. `-k`：会删除已有文件的重命名被跳过；
8. `-a`：检测到删除性重命名即中止；
9. `-d -v`：执行删除性重命名，`-v` 以 `(*)` 标记；
10. 交互模式：回答 `n` 不改；非法回答重新提示 `Yes or No?`；回答 `y` 执行；
11. 替换模式含路径、含通配符、`#n` 越界：均报错退出 1；
12. 无匹配、替换结果为空串：报错退出 1 且不改文件；
13. `'x\#1'`：`\#` 生成字面量 `#`。

## 编译步骤

```bash
make -j1 CC=<profile 中的 clang> CFLAGS='-std=gnu89 -O2 -fPIE -static-pie'
```

上游 Makefile 的规则是 `$(CC) -o ren $(CFLAGS) ren.c`，编译与链接一步完成，所以链接选项
也放在 CFLAGS 中。配方从 `tools.build:compiler_executables` 取编译器，命令行变量覆盖上游
默认值，不依赖 shell 环境变量（R33）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ren.c:309:9: error: use of undeclared identifier 'MAXNAMLEN'`（3 处） | glibc 的 `<dirent.h>` 在 `__USE_MISC` 下定义 BSD 宏 `MAXNAMLEN`；musl 只在 `<sys/param.h>` 定义（OHOS sysroot 仅 `sys/param.h:6` 有 `MAXNAMLEN 255`） | 补丁 `0001-ren.c.patch` 加一行 `#include <sys/param.h>`，无平台宏；沉淀为知识草稿 E620-draft-2562 |
| 2 | K&R C：隐式 int、隐式函数声明、旧式函数定义 | 1988 年源码。OHOS clang 15.0.4 在默认 gnu17 下只告警，但 GCC 14、clang 16+ 在 C99 及以后的模式下把隐式声明当错误（主机 GCC 14 实测 6 个 error） | 用源码本身的语言标准 `-std=gnu89` 编译（GCC 14 实测 0 error），不依赖编译器默认标准；clang 对 malloc/strlen 等 6 个库函数按正确原型隐式声明（告警原文 `implicitly declaring library function 'malloc' with type 'void *(unsigned long)'`），不存在 64 位指针截断 |
| 3 | `conan create` 的 `source()` 报 `sha256 hash failed`：Provided `6ccf51b4…`，Computed `1f591697…` | ibiblio 对该 `.tar.gz` 附带 `Content-Encoding: gzip/x-gzip`，requests 下载器交付的是解码后的 51200 字节 tar 流（`gzip -dc` 原始包即得 `1f591697…`，逐字节一致），不是官方归档字节 | conandata 记录官方归档字节的 sha256（curl 与 CI 预下载 predl 得到的就是这些字节）；`source()` 在 `get()` 抛 `ConanException` 后用 urllib 重新下载原始字节（urllib 不解码 Content-Encoding），`check_sha256` 通过后解包。同形态先例：已合并的 blepvco 0.1.0；已有草稿 E561-draft-4FE2、DRAFT-conan-downloader-xgzip-content-encoding 已覆盖，不重复沉淀 |
| 4 | x86 运行器无法执行动态链接的 OHOS 产物（缺 `/lib/ld-musl-aarch64.so.1`） | 交叉目标的动态加载器不在构建机上 | 只依赖 libc 的工具以 `-static-pie` 链接：交付物本身无需加载器，qemu-aarch64 可直接运行打包产物，同时保留 PIE 与 full RELRO（readelf：`Type: DYN`、`FLAGS BIND_NOW`、`FLAGS_1 NOW PIE`） |

技术债务（P006）：`-std=gnu89` 是为 K&R 源码选择的语言标准，不是屏蔽告警；如果上游补全
函数原型与头文件，可以去掉。

## 源码修改

- `patches/0001-ren.c.patch`：在 `#include <sys/types.h>` 后加 `#include <sys/param.h>`，
  +1/-0，由 `refresh-patch --auto` 生成。

## 依赖版本

无第三方依赖；只链接 OHOS musl libc（静态）。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify ren 1.0
# G1 / G2 / G3 / G4 / L2 / L4 / L5 全部 PASS
# source(): "conan download failed (... sha256 hash failed ...); retrying without Content-Encoding decoding" 后通过
# RUN: make -j1 CC=/data/service/hnp/bin/clang CFLAGS='-std=gnu89 -O2 -fPIE -static-pie'
# bin/ren: ELF 64-bit LSB pie executable, ARM aarch64, static-pie linked
# test_package: [ok] ren: 13/13 functional checks passed（qemu-aarch64 执行打包产物）
# HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...}
```

```bash
python3 scripts/ohc-run.py finish ren 1.0 built
# W3 本地 CI（ci/conan/setup.sh + build_and_test.sh）：通过
#   KC / JC 通过；Pre-download 用 curl 取得官方原始字节，conandata 改写为 file:// 后
#   "Sources correctly downloaded from file://.../predl_cache/..._ren-1.0.tar.gz"（sha256 校验通过）
#   test_package: [ok] ren: 13/13 functional checks passed
# Step 3 G0 clean-verify 执行 ./configure 报 exit 127：G0 按 autotools 流程构建，
#   本包没有 configure（纯 Makefile），属非阻塞步骤的工具局限，不影响配方
```

两条源码下载路径都已实测：conan-verify 直接 `conan create` 走 `get()` 失败 → urllib 原始字节
回退；W3 走 CI 预下载（curl 原始字节 → `file://`）。两者校验的都是官方归档的 sha256。

test_package 的 13 个场景在 x86_64 运行器上通过 qemu-aarch64 执行的是 Conan 打包出的同一个
static-pie 二进制，不是另行重链的副本；AArch64 设备上则直接执行。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/ren` | AArch64 static-pie 可执行文件 |
| `share/man/man1/ren.1` | 上游 man page |
| `share/doc/ren/README` | 上游 README（来源与作者说明） |

## 注意事项

- 交互模式（不带 `-d`/`-k`/`-a`）要从标准输入读一行回答；标准输入 EOF 时上游代码
  `*fgets(...)` 会解引用 NULL。这是上游行为，本次不改；脚本中使用请加 `-d`、`-k` 或 `-a`。
- 搜索模式中的通配符需要加引号，否则会先被 shell 展开（见 `ren(1)` BUGS 一节）。

## 对话记录

### 对话 #1 — 2026-09-24

- 依赖预检确认无第三方依赖；语言预检判定 C；仓库无 ren 历史归档。
- OHOS clang 编译首错为 `MAXNAMLEN` 未声明，定位到 musl 头文件布局差异，以一行
  `#include <sys/param.h>` 补丁修复，并沉淀知识草稿 E620-draft-2562。
- 首次 conan-verify 在 `source()` 报 sha256 不一致，实测为 ibiblio 的 Content-Encoding
  导致 requests 交付解码后的 tar 流；改为 `get()` 失败后 urllib 取原始字节校验，复验通过。
- 以 `-std=gnu89 -static-pie` 构建；test_package 13/13 在 qemu-aarch64 上通过；W3 通过。
---

**编译结束**: 2026-09-24 01:55
**最终状态**: built
