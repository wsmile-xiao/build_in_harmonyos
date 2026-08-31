# unibilium 2.1.2 测试报告

> **项目**: unibilium
> **测试日期**: 2026-08-30
> **测试环境**: HarmonyOS PC aarch64 (Clang 15.0.4, Conan 2.29.1)
> **测试类型**: 官方测试套件 + 消费者测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 3690 | 100% |
| 通过 (PASS) | 3690 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** — 上游官方测试套件 3678/3678 全部通过，test_package 消费者测试 12 项断言全部通过。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无 | - | - |

### 2.3 可用功能清单

```
✅ terminfo 文件读取/写入（unibi_from_file/from_fp/from_fd/from_mem）
✅ 终端数据库加载（unibi_from_term/from_env/unibi_terminfo_dirs）
✅ 能力集读写（boolean/numeric/string，含扩展能力 ext_bool/ext_num/ext_str）
✅ terminfo 格式字符串解释（unibi_run/unibi_format）
✅ 终端序列化（unibi_dump + unibi_from_mem 往返）
✅ 名称/别名管理（unibi_get/set_name、unibi_get/set_aliases）
✅ 能力名映射辅助（unibi_name_*/unibi_short_name_*）
```

### 2.4 已知限制

1. 无（纯 C 库，无外部依赖，完整编译运行）

---

## 三、测试详情

### 3.1 上游官方测试（make test，prove 驱动，t/ 目录 9 个测试文件）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| t/00_load.c | 创建/销毁 dummy terminal | ✅ PASS |
| t/if-then-else.c | terminfo if/then/else 格式表达式求值 | ✅ PASS |
| t/wide-format.c | 宽字符 terminfo 格式字符串 | ✅ PASS |
| t/static_screen.c | screen terminfo 条目能力断言 | ✅ PASS |
| t/static_screen-256color.c | screen-256color 条目能力断言 | ✅ PASS |
| t/static_tmux.c | tmux 条目能力断言 | ✅ PASS |
| t/static_xterm.c | xterm 条目能力断言 | ✅ PASS |
| t/static_xterm-256color.c | xterm-256color 条目能力断言 | ✅ PASS |
| t/new-extended-format-static_screen.c | 扩展格式从文件加载（t/fixtures/s/screen） | ✅ PASS |

上游测试命令：`prove -f t/*.t` → **Files=9, Tests=3678, Result: PASS**

### 3.2 test_package 消费者测试（Conan L1 测试，R34 实质 API 调用）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| unibi_dummy() | 终端对象创建 | ✅ PASS |
| unibi_set_name/get_name | 名称往返 | ✅ PASS |
| unibi_set_bool/get_bool | 布尔能力往返 | ✅ PASS |
| unibi_set_num/get_num | 数值能力往返 | ✅ PASS |
| unibi_set_str/get_str | 字符串能力往返 | ✅ PASS |
| unibi_set_aliases/get_aliases | 别名读写 | ✅ PASS |
| unibi_dump()/unibi_from_mem() | 序列化/反序列化 | ✅ PASS |
| 能力经 dump/from_mem 往返存活 | 完整性 | ✅ PASS |
| unibi_short_name_bool() | 能力短名查询 | ✅ PASS |
| unibi_run() | 格式字符串求值 | ✅ PASS |
| unibi_destroy() | 对象销毁 | ✅ PASS |

test_package 断言数：**12**（在 conan create 中执行，1/1 Passed）

### 3.3 pkg-config 消费验证（W4 P1-1 修复）

| 检查项 | 内容 | 结果 |
|--------|------|------|
| .pc 文件存在 | `lib/pkgconfig/unibilium.pc` 位于包内 | ✅ PASS |
| Name 字段 | `Name: unibilium` | ✅ PASS |
| Libs 字段 | 含 `-lunibilium` | ✅ PASS |
| relocatable prefix | 含 `${pcfiledir}/../..`（pkg-config 可解析到 prefix） | ✅ PASS |
| Cflags/Libs 展开 | 含 `-I${includedir}` 与 `-L${libdir}` | ✅ PASS |

> CI 环境无 pkg-config 命令，test_package test() 用 Python 模拟 pkg-config 解析 .pc，验证下游（libtermkey）消费所需的关键字段，确保 .pc 可被真实消费。

### 3.4 Conan 配方验证（conan-verify 门禁）

| 门禁 | 结果 |
|------|------|
| G0 预构建风险评估 | ✅ PASS |
| G1 配方完整性 | ✅ PASS |
| G2 conan create（干净构建） | ✅ PASS |
| G3 系统同名库隔离 (R26) | ✅ PASS |
| G4 产物完整性 | ✅ PASS |

**产物**: `libunibilium.a`（静态库）+ `unibilium.h` + `lib/pkgconfig/unibilium.pc`

---

**测试结论**: 上游 3678 项断言 + 消费者 12 项断言全部通过，通过率 100%，可提交 PR。