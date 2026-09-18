# libmaa 1.4.7 适配笔记

## 编译环境
- 构建系统: BSD make (mkc / mk-configure) — GNU make 不兼容，配方按等价步骤直接编译
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4（OHOS SDK，`tools.build:compiler_executables` 注入）
- 状态: built

## 官方来源
- 上游: https://downloads.sourceforge.net/project/dict/libmaa/libmaa-1.4.7/libmaa-1.4.7.tar.gz
- SHA-256: 4e01a9ebc5d96bc9284b6706aa82bddc2a11047fa9bd02e94cf8753ec7dcb98e
  （与 Debian/Ubuntu `libmaa_1.4.7.orig.tar.gz` 一致，sha1 7406e7171c6fba4dba3f96244abc0715f0f4fee5）
- 说明: 历史归档曾记录本地路径的源码来源，本适配已按任务要求恢复为官方 HTTPS 源并重新核验哈希
  （SHA-256 与 Debian/Ubuntu `libmaa_1.4.7.orig.tar.gz` 一致）。

## 编译步骤（conanfile.py build() 等价实现）
1. `awk -f arggram2c arggram.txt > arggram.c`（arg.c 依赖的生成源）
2. 全量编译 24 个源文件（含 bit.c、timer.c）为 -fPIC 目标文件
   - `-DSIZEOF_LONG=8`：aarch64 long=8（mkc 的 MKC_CHECK_SIZEOF 等价检测结果）
   - `-DHAVE_HEADER_SYS_RESOURCE_H=1`：mkc 头文件检测等价；OHOS 实际提供 sys/resource.h
3. 静态库 libmaa.a + 动态库 libmaa.so.4.0（含 soname 软链）
4. 安装头文件 maa.h 与库文件

## 平台适配点（本次新增/修复）
| # | 问题 | 根因 | 方案 |
|---|------|------|------|
| 1 | 历史排除 timer.c（"musl 缺 sys/resource.h"） | mkc 头检测宏 HAVE_HEADER_SYS_RESOURCE_H 未定义时跳过 include，struct rusage 不完整 | 探针实测 OHOS 提供 sys/resource.h 与 getrusage；配方注入该宏，timer.c 全量编译并通过鸿蒙专项测试 |
| 2 | bit.c 需 SIZEOF_LONG | aarch64 long=8 | -DSIZEOF_LONG=8，64 位 popcount 分支实测正确 |
| 3 | BSD make (mkc) 与 GNU make 不兼容 | 上游用 .for/.include <mkc.*.mk> | 配方 build() 直接以等价 clang 命令编译，无需 Makefile.gnu 补丁（历史补丁已移除） |

## 测试
- 上游测试: tests/ 下 18 个独立测试程序全部编译并运行通过（输出与 expect.out 一致），
  详见 reports/upstream-test-ledger.md（双口径 18/18 = 100%）。
- 鸿蒙专项测试: test_package/ohos_special_test.c — 验证 timer(getrusage) 与 bit(SIZEOF_LONG=8)。
- 消费者测试: test_package/test.c — 调用 maa_version / hsh_* / str_pool_* 公开 API。

## 依赖版本
- 无第三方依赖（requirements() 为空）

## 验证结果
- conan-verify 8 道门禁全通过（G1/G2/G3/G4/L2/L4/L5）
- conan create + test_package 2/2 测试通过

## 注意事项
1. 上游 timer.c 的 DIFFTIME 宏对 tv_usec 做整数除法，亚秒精度截断为 0（上游固有行为，与平台无关）
2. bit_tst 返回 int，第 63 位掩码 0x8000000000000000 截断为 int 后为 0（上游固有行为）

---

### 对话 #1
**用户**: pc1-15 绑定 libmaa 读取并执行最新任务（libmaa-1.4.7-r01-pc1-15-20260915T184405Z）
**执行**: 完整适配流程 —— 创建 worktree feat/libmaa-1.4.7（从 main 090ac16c60 创建）→ 官方源下载核验 →
lang-preflight（c↔cpp 兼容）→ 全量编译 → conan-init/conan-verify 全通过 →
上游 18 测试全过 + 鸿蒙专项 + 消费者测试 → finish W3 通过 → 知识查重/路径判定 → PR 交付。
**结果**: 适配完成，测试通过率 18/18 (100%)，状态 built。

**编译结束**: 2026-09-16
**最终状态**: built
---

**编译结束**: 2026-09-16 03:43
**最终状态**: built
