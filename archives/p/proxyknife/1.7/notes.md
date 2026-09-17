# proxyknife 1.7 适配笔记

## 编译环境
- 构建系统: autotools（tarball 内含 2006 年生成脚本）
- 编译日期: 2026-09-13
- 编译器: clang 15 / clang++（OHOS aarch64 真机）
- 状态: built

## 编译步骤

1. W0 预检：`bash ci/scripts/preflight_check.sh proxyknife/1.7` 通过（无依赖声明，零外部依赖）。
2. W0b：归档树无 proxyknife 同名/同版本；recipe-search 语料 4469 条无相似配方，首稿走 conan-init 模板。
3. 探索编译（`~/tmp/uc2` 外的 builds/proxyknife-1.7.work）：
   - `./configure --prefix=$DEFAULT_PREFIX --disable-nls CFLAGS="-fcommon -O2"`（CC=clang）
   - `make -j1 && make install DESTDIR=$TEST_PREFIX`
   - `proxyknife --version` 输出 GNU Proxyknife 1.7。
4. conan-init → 人工定制配方（application 型）→ conan-verify（G0-G4 + L2/L4/L5 全 PASS）。

## 上游测试账本（四维）

- 上游源码静态声明总数 N_static = 0：源码树无 tests/ 目录、无 *.c 测试文件、无 dejagnu/autotest 注册；Makefile.in 由 automake 生成，含空 `check` 目标但未注册任何测试。
- 实际执行数 N_executed = 0（上游无测试可执行）。
- 跳过数 = 0。
- 新增消费者测试 N_consumer = 1（test_package/test_proxyknife.py，3 项断言：--version 横幅、--help 用法、未知选项非零退出），conan create 内执行全过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cannot guess build type` | 2005 版 config.guess 无 HarmonyOS 分支（E007） | build() 内用 automake 工具链包自带（认识 ohos）的 config.guess 构建期覆盖上游文件 |
| 2 | `Kernel 'linux' not known to work with OS 'ohos'` | config.sub 缺 linux-ohos 内核配对（E072） | 同 1：config.sub 一并由 automake 包构建期覆盖（其 kernel-os 白名单已含 `linux-ohos*`） |
| 3 | config.status 临时目录 Permission denied | HMDFS UID 映射 + umask 077（E011） | sed configure 中 umask 077→022（2 处） |
| 4 | doc/proxyknife.1 生成失败（POD document had syntax errors） | 2007 年 POD 源与现代 pod2man 不兼容 | Makefile.am/Makefile.in 的 SUBDIRS 去掉 doc（工具不依赖 man page） |
| 5 | `use of undeclared identifier 'LC_CTYPE'` | musl 不经其他头间接暴露 LC_* 宏 | src/proxyknife.c 补 `#include <locale.h>` |
| 6 | 链接 duplicate symbol（dict/debug/progname 等） | proxyknife.h 在每个 TU 定义全局变量，clang ≥10 默认 -fno-common | configure 传 CFLAGS="-fcommon -O2"（E491/E163 同类先例） |

## 源码修改（补丁 4 个 + 构建期替换 2 个）

- 0001/0002：SUBDIRS 去 doc（Makefile.am + Makefile.in 同步）。
- ~~0003/0004（config.guess/sub 整文件替换）~~ → 2026-09-15 改为**构建期替换**：build() 用 `tool_requires("automake/1.18")` 包内的 config.guess/config.sub 覆盖上游 2005 版（E007）。原整文件补丁共 6012 行使 PR 达 6441 行、超出 AI 检视体积上限（平台提示“变更过大，本次跳过”，规则 6 无法拿到结论），故切换为零 diff 的构建期方案。
- 0005：configure umask 077→022（E011）。
- 0006：src/proxyknife.c 补 locale.h。

## 依赖版本

无外部依赖（零依赖工具包）。

## 验证结果

```bash
bash ci/scripts/preflight_check.sh proxyknife/1.7   # PASS
python3 scripts/ohc-run.py conan-verify proxyknife 1.7
# G1/G2(conan create)/G3/G4/L2/L4/L5 全 PASS，消费者测试 3/3 断言通过
```

## 注意事项

- config.guess/config.sub 为构建期替换（E007）：源文件内容不随归档携带，PR diff 保持小体积。
- 工具型包（application），软件级 commands.json 已声明。
- NLS 全禁用（--disable-nls），无 msgfmt 依赖；文档未构建（POD 源不兼容现代 pod2man，见补丁 0001/0002）。
- 路径 A，无跨仓库新知识增量（-fcommon 已有 E491/E163，config 三元组已有 E007/E072），不走路径 B。
---

**编译结束**: 2026-09-15 21:01
**最终状态**: built
