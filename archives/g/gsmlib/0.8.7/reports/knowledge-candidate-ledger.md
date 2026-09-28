# gsmlib 0.8.7 知识候选台账与查重（task_id: gsmlib-0.8.7-r02-pc2-48-20260926T180000Z）

## 候选清单（非噪声）

| # | 候选（真实错误/根因/修复） | 验证 | 适用范围 | 四范围查重 | 路径决定 |
|---|------|------|----------|-----------|----------|
| C1 | config.guess/config.sub 不识别 HarmonyOS/linux-ohos 三元组；configure 报 cannot guess build type | conan-verify G2 通过（配置阶段修复后全门禁绿） | 任何 2008 版 config.guess 的 autotools 库 | 图谱 E007（config.guess 分支）、E122（config.sub kernel-ohos）、E160（HarmonyOS 识别）均已存在 | 复用已有知识（reuse_existing） |
| C2 | 2003 年代 C++ 代码在 C++17 下 throw(...)/register/narrowing 诊断升级为 error | conan-verify G2 通过（降级为 warning 后编译绿） | 任何 legacy C++ 库 | 图谱 E293 已存在 | 复用已有知识（reuse_existing） |
| C3 | 老 C++ 库 new[] 分配配标量 delete（alloc-dealloc-mismatch），ASAN 报错、Release 下 SMS 解码测试 SIGSEGV | ASAN 定位 + 补丁 0004 修复后测试复跑 | 任何 C++ 库（堆分配释放配对错误） | 图谱/正式知识/草稿/归档语料均无命中 | new_draft（路径 B） |
| C4 | autotools 多目录 Makefile.in 在 out-of-tree（VPATH/conan build dir）下 `<lib/xxx.h>` 头找不到，INCLUDES=-I.. 不足 | conan-verify G2 通过（四目录 Makefile.in 加 -I$(top_srcdir) 后编译绿） | 任何 autotools 库含 `#include <lib/...>` 自引用头 | 图谱 E041/E071/E110/E175/E434 均不覆盖（automake 版本/config.status 权限/copystamp 主题不同）；正式知识/草稿/归档语料无命中 | new_draft（路径 B） |

## 七轴查重

### C3（new[]/delete 不匹配 → alloc-dealloc-mismatch SIGSEGV）
- exact_duplicate: 无（图谱/正式知识/草稿/归档语料均未发现同名条目）
- causal_duplicate: 无（无条目描述 new[]/delete 配对错误的崩溃路径）
- trigger_overlap: 低（与 E293 同属"legacy C++ 在 clang/libc++ 下暴露"，但触发面不同：E293 是编译期诊断，C3 是运行期堆损坏）
- solution_overlap: 无（E293 方案是编译标志降级；C3 方案是源码 delete[] 配对修复）
- combination_novelty: 是（ASAN alloc-dealloc-mismatch → SIGSEGV → delete[] 修复的完整链条未见记录）
- boundary_novelty: 是（Release/NDEBUG 下断言被编译掉导致从 abort 变 SIGSEGV 的边界行为）
- test_migration_novelty: 是（SMS 解码类测试在此类缺陷下可稳定复现，可迁移为通用 C++ 内存配对检查用例）
- 结论: 未命中且存在新增差异 → 走路径 B，建立同 stem 草稿

### C4（autotools 多目录 INCLUDES 缺 -I$(top_srcdir)）
- exact_duplicate: 无
- causal_duplicate: 无（E075/E217 是 pkg-config/conan includedirs 环境变量主题，非 Makefile.in INCLUDES 路径）
- trigger_overlap: 中（与 E217 的 "fatal error: xxx.h not found" 表面同触发，但根因不同：E217 是配方安装路径，C4 是 VPATH 构建 include 目录）
- solution_overlap: 无（E217 方案是 CMakeLists 安装 include；C4 方案是 Makefile.in 加 $(top_srcdir)）
- combination_novelty: 是（out-of-tree autotools + 自引用 `<lib/...>` 头 + conan build dir 组合）
- boundary_novelty: 是（同一 INCLUDES 行在 in-tree 构建可过、out-of-tree 构建失败的边界）
- test_migration_novelty: 是（可用最小 autotools 两目录工程复现，迁移为通用构建用例）
- 结论: 未命中且存在新增差异 → 走路径 B，建立同 stem 草稿

## 路径决定
- C1: reuse_existing（E007/E122/E160 覆盖）
- C2: reuse_existing（E293 覆盖）
- C3: new_draft（建立 gsmlib-0.8.7-alloc-dealloc-mismatch-delete-pair 的 .kv/.md 草稿）
- C4: new_draft（建立 gsmlib-0.8.7-autotools-vpath-top-srcdir-include 的 .kv/.md 草稿）
- 总体路径: 路径 B（知识库扩展）——两个 new_draft 与 gsmlib 归档同 PR
