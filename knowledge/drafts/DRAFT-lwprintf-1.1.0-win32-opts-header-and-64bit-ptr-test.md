# DRAFT: 顶层 CMake 无条件选用 win32 专用配置头导致 OHOS 编译失败 + 上游 %p 32 位指针断言

- **草稿 ID**: `DRAFT-lwprintf-1.1.0-win32-opts-header-and-64bit-ptr-test`
- **来源**: lwprintf 1.1.0 HarmonyOS PC 适配（archives/l/lwprintf/1.1.0）
- **状态**: 草稿（待审核提升）
- **同类条目**: `E375`、`E532`、`DRAFT-gamelib-1.9.9-dual-backend-single-header-game-lib`、`DRAFT-E719-opt-3.19-aarch64-unsigned-ub-known-test-fail-gate`

## 问题

lwprintf 1.1.0 上游 `CMakeLists.txt` 顶层工程分支**无条件** `set(LWPRINTF_OPTS_FILE <root>/dev/lwprintf_opts.h)`，
该文件是开发/测试专用的 win32 配置头，内含 `#include "windows.h"` 与 OS 互斥句柄（HANDLE）定义；
`lwprintf/library.cmake` 用 `configure_file` 将其复制为生成态 `lwprintf_opts.h`，
导致 OHOS/Linux 上所有引用 `lwprintf_opt.h` 的编译单元报：

```
lwprintf_opts.h:39:10: fatal error: 'windows.h' file not found
```

顶层分支还无条件加入 win32 系统端口源文件（`lwprintf_sys_win32.c`）、注入
`WIN32 _DEBUG CONSOLE LWPRINTF_DEV` 编译宏并把 `dev/` 目录加入 include 路径。

配套问题：上游测试 `tests/test.c` 的 `%p` 断言按 **32 位指针宽度**写死
（注释明示 "Pointer, 32-bit system"），在 OHOS arm64（64 位指针）下 3 项断言
（`test.c:204-206`）长度不一致（期望 8/10 字符，实际 16/18）。

## 根因

1. 平台专用**配置头**被顶层 CMake 无条件选为默认，未做 WIN32 正向守卫；
   非 Windows 平台没有回落机制（上游自带可移植 `lwprintf_opts_template.h` 但未被使用）。
2. 上游测试断言硬编码 32 位指针假设，未按架构参数化。

## 修复方案（已在 lwprintf 验证）

**补丁 0001（配置头/源文件/宏守卫）**：

```cmake
if(WIN32)
    set(LWPRINTF_OPTS_FILE ${CMAKE_CURRENT_LIST_DIR}/dev/lwprintf_opts.h)
endif()
if(WIN32)
    target_sources(... lwprintf_sys_win32.c)
endif()
if(WIN32)
    target_compile_definitions(lwprintf PUBLIC WIN32 _DEBUG CONSOLE LWPRINTF_DEV)
endif()
if(WIN32)
    target_include_directories(... dev/)
endif()
```

非 WIN32 自动回落 `lwprintf_opts_template.h`（可移植，无平台头）。

**补丁 0002（上游测试可移植化）**：`windows.h` 包含、win32 源文件与 dev include 路径仅 WIN32 启用；
测试断言语义未改。

**%p 断言处理**：不改写断言、不改库；如实记录失败并给出恢复条件
（32 位目标运行或断言按 `PTR_WIDTH` 计算）。全量口径上报 `148/170 = 87.1%`，
执行集合 `148/151 = 98.0%`。

## 验证

| 门禁 | 结果 |
|------|------|
| `conan-verify` G0/G1/G2/G3/G4 | 全部 PASS（OHOS arm64, clang 15） |
| 上游测试（LwLibPROJECT） | 实跑 148 通过 / 3 失败 / 151 执行；台账见 upstream-test-ledger.md |
| OHOS 专项测试 | 13/13 通过（自定义实例、%*K、截断、64 位 %p、int64/uint64） |
| 消费者用例（日志模块） | exit 0（lwprintf_init_ex/snprintf_ex/printf_ex 公开 API） |

## 适用边界

- **适用**：顶层 CMake 把含 windows.h 的 win32 专用配置头**无条件**选为默认的嵌入式 C 库；
  其余平台依赖模板/默认值回落的场景；其上游测试按 32 位指针写 %p 断言的 64 位目标适配。
- **反例**：上游已有正确平台条件化（模板不含平台头 / if(WIN32) 守卫）的库；
  %p 断言按 64 位或 PTR_WIDTH 参数化的库；E375 的"未知系统误判 Windows（NOT UNIX）"场景。

## 关系

- `similar_to`: `E375`（win32 源文件正向选择 + POSIX 能力探测——载体为源文件，本条目为配置头）、
  `DRAFT-gamelib-1.9.9-...`（单头文件产品线选择——header-only + `__has_include`，本条目为编译型库 +
  CMake 显式无条件选择）、`DRAFT-E719-opt-3.19-...`（64 位不能通过的断言用 known-failure 门禁——
  原则同、trigger 不同：%p vs atof/fcvtzu）、`E532`（if WIN32/elseif UNIX/else FATAL 三分支——不同载体）。
- `caused_by`: 无
- `prerequisite_of`: 无
- `conflicts_with`: 无

## 查重结论（七轴）

| 轴 | 结论 |
|----|------|
| `exact_duplicate` | 否（无同配置头条目的完整重复） |
| `causal_duplicate` | 否（根因链独立：无条件 set 配置头 vs 既有条目根因） |
| `trigger_overlap` | 是（与 E375/gamelib 同为 WIN32/windows.h 触发族，载体不同） |
| `solution_overlap` | 部分（E375 正向条件化理念相同；gamelib 平台边界声明的处理原则相近） |
| `combination_novelty` | 是（配置头 configure_file 生成 + 测试 %p 指针宽度的组合无既有覆盖） |
| `boundary_novelty` | 是（配置/选项头层面对比 E375 源文件层面） |
| `test_migration_novelty` | 是（%p 32 位指针假设的上游测试处理，区别于 E719 的 atof/fcvtzu） |

## 决定

`new_draft`（路径 B）：部分重复但有已验证、可跨库复用的新增差异，建立本 .md/.kv 配对草稿，
与 lwprintf 归档文件进入同一 PR。候选 3（CMake 无 install 规则手动装配）完整重复
`DRAFT-fusion-1.3.3-cmake-no-install-rule-manual-package` → `reuse_existing`（路径 A 复用）。