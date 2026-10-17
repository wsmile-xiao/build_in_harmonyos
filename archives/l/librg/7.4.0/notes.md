# librg 7.4.0 适配笔记

## 编译环境
- 构建系统: makefile（聚合头 LIBRG_IMPL 模式，header-library 打包）
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4（OHOS SDK aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

1. 官方源码: https://github.com/zpl-c/librg/archive/refs/tags/v7.4.0.tar.gz（SHA-256: 33b02636a69221aee41c96957d91f065dbfa68b400ba850172b3c4c07bc471d0）
2. 上游单元测试: `make test`（code/tests/unit.c，zpl tester 框架，89 个 IT 用例全过）
3. 上游 apps: `make apps`（8 个示例/基准全部构建成功）
4. 鸿蒙专项测试: test_librg_ohos.c（37 断言全过，aarch64-ohos 二进制本机运行验证）
5. Conan 配方: header-library 模式（librg 无独立库目标，消费者 LIBRG_IMPL 内联编译实现），conan-verify G0-G4+L2/L4/L5 全过
6. W3 本地 CI 模拟: prdiff 模式通过（详见报告）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试编译失败：use of undeclared identifier 'PATH_MAX' | 内嵌聚合头 code/vendor/zpl.h 在 ZPL_SYSTEM_UNIX 分支用 PATH_MAX 定义 ZPL_MAX_PATH，但自身未 #include <limits.h>；glibc 环境被其他系统头传递包含而掩盖，OHOS musl/clang 干净环境暴露 | patches/0001-code-vendor-zpl.h.patch：zpl.h include 区补 `#include <limits.h>` |
| 2 | lang-preflight 判 mixed(npm) 并自动写 env_unsupported 终态 | 工具 manifest 优先级误把 release 工具 package.json（main 指向 C 头文件 code/librg.h）当主体 manifest，与 93% C 源统计矛盾判 mixed | 核实属误判：librg 是纯 C 库（14/15 C 源、Makefile 构建、仅 misc/packager.js 1 个 nodejs 辅助脚本），按边界规则"辅助脚本不算主体"应判 c（c↔cpp 兼容族），继续 C 适配 |
| 3 | W3 本地 CI 模拟 JC5 失败（full 全仓扫描） | 本分支尚无 commit 时 junk_check 回退 full 模式 `git ls-files`，拦到 main 上其他库 util-linux-login/2.42.2/.ci-trigger（0 字节历史基线，commit 761df452e5 已合入，早于本任务） | 按 CI 同构 prdiff 模式（JUNK_PR_DIFF 指向本 PR 9 个文件）重跑 W3；不修改、不提交其他库文件（哈希 e3b0c44298fc... 记录隔离），librg 自身无 junk |

## 源码修改

- code/vendor/zpl.h：补 `#include <limits.h>`（patches/0001-code-vendor-zpl.h.patch，+1/-0，正文件补丁）

## 依赖版本

- 无外部依赖（zpl、enet 均内嵌于 code/vendor/，纯头文件）

## 验证结果

```bash
# 上游单元测试（89/89）
make test   # 4 modules, 89 total, 0 failed, 89 passed

# 上游 apps 构建（8/8）
make apps   # example-enet/example-packing/example-simple/example-unpacking/example-world/library/manual-testing/query-performance

# 鸿蒙专项测试（37/37，aarch64-ohos 二进制本机运行）
/data/service/hnp/bin/clang -std=gnu11 -O2 -Icode test_librg_ohos.c -pthread -lm -o test_librg_ohos && ./test_librg_ohos

# Conan 验证（G0-G4 + L2/L4/L5 全过）
python3 scripts/ohc-run.py conan-verify librg 7.4.0

# W3 本地 CI 模拟（prdiff 模式，JUNK_PR_DIFF 指向本 PR 文件清单）
JUNK_PR_DIFF=<pr.diff> python3 scripts/ohc-run.py finish librg 7.4.0 built
```

## 测试统计（双口径）

- 上游源码声明用例总数: **89**（code/tests/cases/*.h 中 IT() 用例：entity 8 + general 20 + packing 35 + query 26；框架 zpl-c/tester 的 MODULE/IT 宏，unit.c 注册 4 模块）
- 当前配置可执行集合: **89/89**（同一 Makefile test 目标全量编译运行，无互斥分支排除）
- 实际执行通过: **89/89（100%）**；失败 0；未运行 0；未实例化 0
- 鸿蒙专项测试: 37 断言全过（额外新增，非上游用例）

## 知识候选台账 + 七轴查重（路径 B：知识库扩展）

**候选 K1**: 内嵌聚合头 zpl.h 使用 PATH_MAX 但未包含 limits.h → OHOS musl/clang 干净环境编译失败
- 真实错误: `error: use of undeclared identifier 'PATH_MAX'`（code/vendor/zpl.h:10450/10874/10878）
- 根因: ZPL_MAX_PATH 宏在 ZPL_SYSTEM_UNIX 分支引用 PATH_MAX，zpl.h 自身无 `#include <limits.h>`；glibc 下被传递包含掩盖，OHOS musl 下暴露
- 修复: 补 `#include <limits.h>`（patches/0001-code-vendor-zpl.h.patch）
- 验证: 修复后上游 89/89 + 鸿蒙专项 37/37 + conan create 全过
- 适用范围: 任何内嵌 zpl-c/zpl（librg 等）或类似"聚合头用 PATH_MAX 未含 limits.h"的库；跨库可复用
- 查重（四范围）: index.tsv 无命中（E062 gnulib FAM / E065 xzalloc / E115 FALLOC / E117 PACKAGE_STRING / E127 pthread_cancel / E152 CLOCK_* 均不同根因）；doc/ 无命中；graph/E*.kv 无命中；drafts/ 无命中（零覆盖）
- 七轴: exact_duplicate=未命中（无同签名条目）；causal_duplicate=否（既有条目根因均非"缺失 limits.h 传递包含"）；trigger_overlap=部分（E152 同为"undeclared identifier"类触发但符号为 CLOCK_*，根因 feature macro 不同）；solution_overlap=无（E152 用 CFLAGS 宏，本候选用补 include）；combination_novelty=有（"聚合头 + PATH_MAX + musl 传递包含"组合见首例）；boundary_novelty=有（适用于 OHOS/干净 clang 环境边界）；test_migration_novelty=有（89 用例全量迁移验证）
- 关系: similar_to=E152（同为头文件符号未声明，根因不同）；caused_by=（无，上游 zpl.h 自身缺失）；conflicts_with=（无）
- 决定: **new_draft**（E543-draft-2EE3.kv/.md 已建，与三方库归档同 PR）

**候选 K2**（观察登记，非草稿）: lang-preflight 对"带 npm release 工具的纯 C 库"误判 mixed(npm)
- 仅登记为候选观察，不建草稿（工具层问题，属 SKILL_FEEDBACK 范畴；librg 主体为 C，判断不影响适配结论）

## 注意事项

- package.json 的 npm/release-it/docsify 均为发布辅助，非库本体；主体语言 C（兼容族）
- util-linux-login/2.42.2/.ci-trigger 为 main 历史基线（0 字节，commit 761df452e5，哈希 e3b0c442...），非本 PR 引入，未改动未提交
---

**编译结束**: 2026-09-05 05:09
**最终状态**: built
