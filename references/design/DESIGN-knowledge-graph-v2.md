# 知识图谱 v2 — 全新架构设计（推翻 v1，从零构建）

> **日期**: 2026-04-09 | **状态**: 架构定稿 | **决策**: 放弃旧 Markdown 列表结构
>
> **核心主张**: 知识库不应是"68个错误条目的编号列表"，而应是**一张带约束的修复决策图**。
> 每个节点不是"一个错误的描述"，而是"一个诊断→决策→执行的完整路径"。

---

## §0 旧结构为什么必须放弃

### 0.1 旧结构的本质问题

```
旧结构 = 编号列表 (E001 → E002 → ... → E068)
         ↓
    每个"条目" = 一篇 Markdown 文章
         ↓
    文章里有: 错误特征 / 根因 / 解决方案(自由文本代码块)
         ↓
    引擎从中提取信息 → 不可靠（格式不统一、禁止策略混在正文）
```

**根本矛盾**: Markdown 是给人读的写作格式，不是给机器消费的数据格式。
强行让引擎从 Markdown 提取决策信息，就像从小说里提取数据库记录。

### 0.2 旧结构导致的具体 Bug（以 E007 为例）

```
E007 的 Markdown 正文:
  ├── ### 解决方案
  │     "唯一正确做法：打补丁修改 config.guess + config.sub"
  │     > ⚠️ 禁止使用 --build= / --host= 参数绕过    ← 在正文里！
  │     ${SKILL_ROOT}/scripts/patch-autotools-ohos.pl ...  ← 代码块
  │
  └── 引擎 _ep_parse_fix() 扫描代码块:
        ├─ export 行?  无 ✗
        ├─ ./configure 行?  无 ✗
        └─ curl config.guess?  无 ✗ (因为写的是 patch-autotools-ohos.pl)
        → 结果: 匹配失败或回退到硬编码的旧逻辑
           旧逻辑恰好有: case E007) ... --build=aarch64-unknown-linux-gnu
           → 输出了被明确禁止的策略 ❌❌❌
```

**这不是引擎 bug，是数据结构 bug。** 正确的策略和禁止策略在同一个文本块里，
没有机器可区分的结构标记。

---

## §1 新架构核心理念

### 1.1 双消费者模型

知识库有两个消费者，需求完全不同：

| 消费者 | 需求 | 容错要求 | 读取方式 |
|--------|------|---------|---------|
| **脚本引擎** (match_error_pattern) | 精确的字段值：关键词、严重度、推荐方案、禁止模式 | 零容忍——错误策略会导致编译失败 | 键值对提取 |
| **AI/Human** (OpenDesk/开发者) | 完整上下文：根因链、影响范围、权衡分析、相关经验 | 高容错——能理解模糊表述 | 自然语言阅读 |

**结论**: 双轨制。机器数据用结构化格式，人类文档保留 Markdown。
两者通过 ID 关联，分别维护但语义一致。

### 1.2 从"错误列表"到"决策图"

```
旧思维: "出错了 → 找到对应的错误条目 → 读解决方案"

新思维: "出错了 → 进入决策节点 → 
         受约束地选择修复路径 → 执行 → 验证"
         
         每个节点包含:
         [识别] 我是谁？什么特征会触发我？
         [诊断] 为什么会发生？（因果链）
         [决策] 该怎么办？（有序方案列表 + 禁止列表）
         [执行] 能自动修吗？怎么做？
         [关系] 和其他节点有什么联系？
```

### 1.3 约束优先原则

**这是最关键的设计转变。**

旧结构：解决方案是"建议性的"，禁止策略是"注释性的"。
新结构：禁止策略是**第一等公民**，与推荐方案同级且优先级更高。

```
决策流程:
  候选方案生成 → [原则过滤器] → 通过 → 输出
                      ↓ 不通过
                   记录违反 + 降级/拒绝
```

---

## §2 数据格式：KV (Key-Value) 结构化文件

### 2.1 为什么不用 YAML/JSON/TOML

| 格式 | 表达力 | bash 原生解析 | 依赖 |
|------|--------|-------------|------|
| YAML | ★★★★★ | ✗ 需要 yq/python | 外部工具 |
| JSON | ★★★★ | ✗ 需要 jq/python | 外部工具 |
| TOML | ★★★★ | ✗ 需要专门解析器 | 外部工具 |
| **自定义 KV** | ★★★☆ | ✓ grep/cut/awk/sed | **无** |
| Shell 赋值 | ★★☆☆ | ✓ source 直接加载 | 无（安全风险） |

**选择: 自定义 KV 格式。**
理由：
1. ohc-run.py build 运行在最小化环境（可能没有 python/jq/yq）
2. grep/cut/awk/sed 是 POSIX 保证可用的
3. 表达力足够覆盖所有需要的字段（不需要嵌套对象/数组）
4. 人类也可直接阅读和编辑

### 2.2 KV 格式规范

```#====================================================================
# E007.kv — 结构化知识条目（机器消费）
# 对应的人类文档: doc/E007.md
#====================================================================

# ═══ Layer 0: 错误面 (Error Surface) ═══
id:                     E007
trigger_tool:           configure
phase:                  configuration
error_signature:        cannot guess build type|unable to guess system type|config.guess.*unable

# ═══ Layer 1: 识别层 (Recognition) ═══
severity:               2
#  3 = 🔴 blocking (编译完全阻塞)
#  2 = 🟡 medium  (有 workaround 但非最优)
#  1 = 🟢 minor   (警告/可忽略)
#  0 = ✅ resolved
category:               autotools-config
match_keywords:         config.guess, build type, HarmonyOS, autoconf,
                         cannot guess, unable to guess, UNAME_SYSTEM

# ═══ Layer 2: 诊断层 (Diagnosis) ═══
root_cause:             GNU config.guess 无 HarmonyOS 检测分支,
                         uname -s 返回 HarmonyOS 无法匹配任何已知模式
affected_scope:         所有 autotools 项目 (configure 脚本的软件)
verification_cmd:       ./build-aux/config.guess

# ═══ Layer 3: 方案层 (Solution Space) ★ 核心字段 ═══
# 推荐方案（按 priority 升序排列，数字越小越优先）
rec_priority:           1
rec_approach:           download-gnuconfig
rec_description:        从 GNU savannah 下载最新 config.guess/config.sub 替换旧版,
                         新版已含多平台检测增强
rec_command:            
rec_auto_fix:          true
rec_impl:               download-gnuconfig

# 回退方案（当推荐方案不可用时）
fallback_priority:      2
fallback_approach:      patch-autotools-script
fallback_description:  使用内置补丁脚本 patch-autotools-ohos.pl 打补丁
fallback_command:       ${SKILL_ROOT}/scripts/patch-autotools-ohos.pl <config.guess> <config.sub>
fallback_auto_fix:      true
fallback_impl:          run-patch-script

# ═══ 禁止策略 (Forbidden Strategies) ★ 与推荐方案同等重要 ═══
# 格式: forbid_N: pattern | reason | consequence
forbid_1_pattern:      --build=*|--host=*
forbid_1_reason:        导致 configure 误判为交叉编译 (cross_compiling=yes),
                         AC_RUN_IFELSE 等运行时检测全部跳过,
                         生成与实际平台不匹配的 config.h
forbid_1_consequence:   级联错误: gnulib模块选错(E061), 符号未声明(E062), -Werror级联(E063)

forbid_2_pattern:      cross.compiling=yes
forbid_2_reason:        同上——任何进入交叉编译模式的做法都是错误的
forbid_2_consequence:   同上

# ═══ Layer 4: 原则引用 ═══
principles:             P-AUTOTOOLS-001, P-AUTOTOOLS-002

# ═══ 关系图 (Relations) ═══
causes:                 []
caused_by:              [E064]
similar_to:             [E021]
conflicts_with:         []
prerequisite_of:        []

# ═══ 元数据 ═══
doc_file:               doc/E007.md
last_updated:           2026-04-09
source_event:           archives/x/xz/5.6.2/manifest.yaml
```

### 2.3 KV 格式解析规则（供引擎实现参考）

```bash
# 从 .kv 文件提取单个字段值
_kv_get() {
    _file="$1"; _key="$2"
    # 匹配 "key: value"，取冒号后的内容（去除首空格）
    # 自动处理多行续行（下一行以空格开头则拼接）
    sed -n "/^${_key}:/,/^[^[:space:]]/p" "$_file" \
      | head -1 \
      | sed "s/^${_key}:[[:space:]]*//" \
      | sed 's/^[[:space:]]*//'
}

# 提取多值列表（逗号分隔 → 数组）
_kv_get_list() {
    _val=$(_kv_get "$1" "$2")
    echo "$_val" | tr ',' '\n' | sed 's/^[[:space:]]*//'
}

# 检查 forbidden pattern 是否命中
_kv_check_forbidden() {
    _file="$1"; _cmd="$2"
    _i=1
    while true; do
        _pat=$(_kv_get "$_file" "forbid_${_i}_pattern")
        [ -z "$_pat" ] && break
        if echo "$_cmd" | grep -qE "$_pat"; then
            _reason=$(_kv_get "$_file" "forbid_${_i}_reason")
            echo "FORBIDDEN|$_pat|$_reason"
            return 1
        fi
        _i=$((_i+1))
    done
    return 0
}
```

**零外部依赖。纯 POSIX shell。**

---

## §3 文件系统布局

```
knowledge/
│
├── graph/                          # ★ 新：图谱数据（机器消费）
│   ├── index.tsv                   # 主索引（所有条目的一行摘要）
│   ├── principles.kv              # 原则库（所有原则的定义）
│   ├── E007.kv                    # 条目结构化数据
│   ├── E001.kv
│   ├── E002.kv
│   ├── ...
│   └── _template.kv               # 新建条目的模板
│
├── doc/                            # ★ 新：详细文档（人类/AI 阅读）
│   ├── E007.md                     # E007 的完整诊断报告
│   ├── E001.md
│   ├── ...
│   └── principles.md              # 原则库的人类可读版
│
├── error-patterns.md               # 保留：导航页（指向 graph/ 和 doc/）
├── error-patterns-core.md         # 保留：向后兼容（逐步废弃）
├── error-patterns-compile.md      # 保留：向后兼容（逐步废弃）
├── error-patterns-runtime.md      # 保留：向后兼容（逐步废弃）
│
└── DESIGN-knowledge-graph-v2.md   # 本设计文档
```

### 3.1 主索引 index.tsv 格式

TSV (Tab-Separated Values) —— 引擎的第一站，全量扫描此文件即可：

```tsv
id	severity	category	trigger_tool	phase	keywords	forbidden_count	auto_fix	approach	principles	doc
E007	2	autotools-config	configure	configuration	config.guess,build type,HarmonyOS	2	true	download-gnuconfig	P-AUTOTOOLS-001,P-AUTOTOOLS-002	doc/E007.md
E001	3	toolchain	configure	configuration	cc not found,C compiler,clang,PATH	0	true	set-env-var	CC=clang	doc/E001.md
E002	3	environment	configure	configuration	/tmp,read-only,erofs,TMPDIR	0	true	set-env-var	TMPDIR=$HOME/tmp	doc/E002.md
E005	2	linking	make	compilation	relocation,-fPIC,R_AARCH64,PIC	0	true	add-cflags	CFLAGS=-fPIC $CFLAGS	doc/E005.md
E012	3	toolchain	configure	configuration	ar command not found,llvm-ar,RANLIB	0	true	set-env-var	AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm	doc/E012.md
```

**为什么用 TSV 而不是继续用 Markdown 表格**:
- `cut -f3` 取第 3 列 vs 从 Markdown 表格 `| ... |` 中解析列：复杂度差 10 倍
- `grep -P '\t'` 快速定位
- 可用 `sort -t$'\t' -k2 -rn` 按严重度排序
- Excel/Google Sheets 可直接打开编辑

### 3.2 graph/ vs doc/ 的职责分工

| 维度 | graph/*.kv | doc/*.md |
|------|-----------|----------|
| **读者** | 脚本引擎 | AI / 人类开发者 |
| **内容** | 决策所需的精确字段 | 完整的诊断过程和背景 |
| **格式** | KV 键值对 | 富文本 Markdown |
| **大小** | 每条目 ~40 行 | 每条目 ~100-200 行 |
| **更新频率** | 每次发现新模式时 | 需要深入分析时 |
| **示例字段** | `forbid_1_pattern: --build=*` | ASCII 图、对比表格、代码示例 |

---

## §4 原则库 (principles.kv) 完整定义

原则集中定义在 `graph/principles.kv`，不再分散在各条目中：

```#====================================================================
# principles.kv — 知识图谱 Layer 4: 原则库
# 定义跨条目的通用约束规则。
# match_error_pattern v3 在输出方案前，会用这些原则做过滤。
#====================================================================

# ═══ P-AUTOTOOLS-001: 禁止 --build/--host 绕过 ═══
id:                     P-AUTOTOOLS-001
name:                   禁止 --build/--host 绕过系统检测
level:                  critical
# critical = auto_reject (自动拒绝含此模式的方案)
# high     = auto_warn  (警告但不阻止)
# medium   = log_only  (仅记录)
scope:                   E007, E064
statement:              鸿蒙是原生编译环境(aarch64)，不是交叉编译。
                         使用 --build/--host 绕过 config.guess 会导致:
                         cross_compiling=yes → AC_RUN_IFELSE 跳过 → config.h 错误
forbid_1_pattern:       --build=.*linux-|--host=.*linux-
forbid_1_auto_reject:   true
forbid_1_suggest:       使用 download-gnuconfig 或 patch-autotools-ohos.pl
forbid_2_pattern:       --build=.*gnu|--host=.*gnu
forbid_2_auto_reject:   true
forbid_2_suggest:       同上

# ═══ P-AUTOTOOLS-002: conftest 必须能正常执行 ═══
id:                     P-AUTOTOOLS-002
name:                   conftest 必须能正常执行
level:                  critical
scope:                   E064, E061, E062, E063, E065
statement:              configure 通过编译+执行 conftest 检测平台能力。
                         鸿蒙上首次执行二进制需安全弹窗确认。
                         弹窗超时 → configure 误判交叉编译 → 级联错误。
forbid_1_pattern:       cross.compiling=yes
forbid_1_auto_reject:   false
forbid_1_suggest:       先手动触发安全弹窗，再用 ac_cv_* 缓存变量

# ═══ P-PATCH-001: 修改生成文件必须存为 .patch ═══
id:                     P-PATCH-001
name:                   修改生成文件必须保存为 .patch
level:                  high
scope:                   E058, E059, E007, E008, E063
statement:              configure/Makefile/config.h 是 autotools 生成文件。
                         sed 修改后必须存为 .patch，否则 distclean 后丢失。
forbid_1_pattern:       sed -i.*(configure|Makefile|config\.h)
forbid_1_auto_reject:   false
forbid_1_suggest:       确认 patches/ 目录有对应 .patch 文件

# ═══ P-PATCH-002: __OHOS__ 守卫是平台隔离标准写法 ═══
id:                     P-PATCH-002
name:                   __OHOS__ 守卫是平台隔离的标准写法
level:                  high
scope:                   E008, E011, E051, E060, E004, E020
statement:              #ifdef __OHOS__ 是 clang 自动定义的宏，精确唯一。
                         禁止 #ifndef __linux__ (排除 BSD/macOS) 和
                         硬编码路径 (/data/service/hnp/)。
forbid_1_pattern:       #ifndef\s*__linux__
forbid_1_auto_reject:   true
forbid_1_suggest:       改为 #ifdef __OHOS__

# ═══ P-PATCH-003: 补丁必须可向上游提交 ═══
id:                     P-PATCH-003
name:                   补丁必须可向上游提交
level:                  medium
scope:                   E058, E059, E060, E008, E039
statement:              遵循上游编码风格。英文注释(HarmonyOS: reason格式)。
                         不引入鸿蒙特有 SDK/API 依赖(除非绝对必要)。
forbid_1_pattern:
forbid_1_auto_reject:

# ═══ P-CFLAGS-001: CFLAGS hack 必须记录为技术债务 ═══
id:                     P-CFLAGS-001
name:                   CFLAGS hack 必须记录为技术债务
level:                  medium
scope:                   E005, E011, E032, E033, E063
statement:              CFLAGS/CPPFLAGS/LDFLAGS 强制绕过编译错误时，
                         必须在 notes.md 记录技术债务及期望的上游修复方式。
forbid_1_pattern:
forbid_1_auto_reject:

# ═══ P-RUNTIME-001: 未实现 syscall 必须调用前拦截 ═══
id:                     P-RUNTIME-001
name:                   未实现 syscall 必须在源码调用前拦截
level:                  critical
scope:                   E051
statement:              setreuid/setregid 的 SIGSYS 不可被 handler 捕获,
                         进程直接终止(exit 159)。信号处理方案完全不可行。
                         必须用 #ifdef __OHOS__ 在调用前 return ENOSYS。
forbid_1_pattern:       signal\(SIGSYS
forbid_1_auto_reject:   true
forbid_1_suggest:       用 #ifdef __OHOS__ 在调用前 return ENOSYS

# ═══ P-RUNTIME-002: RPATH 必须覆盖所有 NEEDED 库 ═══
id:                     P-RUNTIME-002
name:                   RPATH 设置必须覆盖所有 NEEDED 库
level:                  high
scope:                   E042, E019, E052
statement:              可移植包 RPATH 必须: 主程序 → 共享库 → 扩展模块,
                         任何一层遗漏都会在目标机出现 ImportError。
forbid_1_pattern:
forbid_1_auto_reject:

# ═══ P-TOOLCHAIN-001: 必须使用 LLVM 工具链 ═══
id:                     P-TOOLCHAIN-001
name:                   必须使用 LLVM 工具链
level:                  high
scope:                   E012, E053
statement:              鸿蒙 SDK 只有 LLVM/Clang。ar/ranlib/nm/strip 用 llvm-* 版本。
                         C++ 编译器是 clang++ (无 cc1plus)。
forbid_1_pattern:       \bar\b(?!llvm-ar)
forbid_1_auto_reject:   false
forbid_1_suggest:       export AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm
```

---

## §5 内置 auto_fix_impl 实现

每个 `rec_impl:` / `fallback_impl:` 字段对应引擎中的一个内置函数：

| impl 名 | 功能 | 适用模式 | 实现要点 |
|---------|------|---------|---------|
| `download-gnuconfig` | 从 git.savannah.gnu.org 下载最新 config.guess + config.sub | E007 | curl -fsSL 下载 → chmod +x → 备份旧版 |
| `set-env-var` | 设置 CC/CXX/AR/CFLAGS/LDFLAGS 等 env var 后重试 | E001,E002,E005,E011,E012,E013,E014,E015,E032 | 将 rec_command 拼接到 ./configure 后面 |
| `add-configure-flag` | 给 configure 追加特定 flag | E006(no-asm),E016(--disable-asm),E027(--disable-nls),E030(--disable-mpers) | 同上 |
| `run-patch-script` | 调用 SKILL 内置补丁脚本 | E007(priority1 fallback) | 检查脚本存在性 → 执行 |
| `replace-symlink-with-copy` | ln → cp | E050 | find symlinks → rm → cp |
| `fix-shebang` | 批量修正 shebang | E037,E049 | sed 's|\#!/usr/bin/env \(\w\+\) |\#!/bin/\1|' |
| `disable-werror` | Makefile 中精准禁用 -Werror | E063 | sed -i 加 CFLAGS += -Wno-error=xxx |
| `skip-test` | 加入排除候选列表 | E022-E024,E031,E046-E048 | echo test_name >> exclude-candidates.txt |
| `none` | 仅输出方案描述，不自动执行 | 默认 | log_info 显示方案 |

---

## §6 引擎 v3 完整流程

```
                    ┌──────────────────────┐
                    │  日志末尾 N 行输入    │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Phase A: 粗筛         │
                    │ scan index.tsv        │
                    │ 对每行的 keywords 做   │
                    │ 固定字符串匹配(F)      │
                    │ 计算原始分            │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Phase B: 精排         │
                    │ 取 Top-3 候选         │
                    │ 加载对应 .kv 文件     │
                    │ 用 error_signature    │
                    │ 做正则精确匹配加分   │
                    │ phase_match 加分      │
                    │ → 最终排序            │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Phase C: 方案生成     │ ← ★ 核心
                    │                        │
                    │ 1. 取最佳匹配的 .kv    │
                    │ 2. 读 rec_approach     │
                    │ 3. 读 rec_auto_fix     │
                    │ 4. 读 rec_impl         │
                    │ 5. 读 forbid_* 字段    │
                    │ 6. 读 principles 引用  │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Phase D: 原则过滤 ★   │
                    │                        │
                    │ for each principle_id  │
                    │   in principles 字段:  │
                    │   load principle.kv    │
                    │   check forbid_pattern │
                    │   against 当前方案      │
                    │   if hit:              │
                    │     if auto_reject:    │
                    │       → 拒绝, 尝试    │
                    │         fallback       │
                    │     else:              │
                    │       → 警告, 继续    │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Phase E: 输出 & 执行   │
                    │                        │
                    │ if 通过所有检查:       │
                    │   显示 doc/ 引用的详情 │
                    │   调用 rec_impl 函数   │
                    │   设置重试标志         │
                    │ else:                  │
                    │   显示方案但标记手动   │
                    └────────────────────────┘
```

### 6.1 评分公式

```
total_score =
    keyword_hit_count          # match_keywords 中命中的关键词数
  × severity_weight            # severity: 3→×3, 2→×2, 1→×1
  + signature_bonus            # error_signature 正则精确匹配: +5
  + phase_bonus                # trigger_tool/phase 与当前步骤匹配: +3
  - principle_penalty          # 如方案触发原则警告: -2
```

---

## §7 关系图数据模型

### 7.1 存储位置

关系存储在每个 `.kv` 文件的 `causes:`, `caused_by:`, `similar_to:`, `conflicts_with:`, `prerequisite_of:` 字段中。
索引文件 `graph/relations.tsv` 提供全局视图：

```tsv
from	to	relation	type	description
E064	E061	causes	conftest失败→gnulib选错模块
E064	E062	causes	conftest失败→符号未声明
E064	E063	causes	conftest失败→Werror级联
E054	E064	caused_by	安全弹窗→conftest超时
E007	E021	similar_to	同为configure阶段问题
E008	E046	similar_to	同为权限限制表现
E046	E047	similar_to	同为HMDFS权限行为
E007	--build	conflicts_with	--build绕过与正确方案冲突
```

### 7.2 引擎利用关系图的场景

| 场景 | 利用方式 |
|------|---------|
| **批量修复** | 修好 E064 后，自动重新评估 E061/E062/E063 是否还需处理 |
| **防误判** | E008("Permission denied") 和 E046("chmod不生效") 特征相似，`similar_to` 帮助区分 |
| **冲突检测** | E007 的 `conflicts_with` 含 `--build=`，引擎看到此方案时直接排除 |
| **根因优先** | 同时命中多个模式时，优先修复无 `caused_by` 的（即根因节点） |

---

## §8 迁移计划

### Phase 0: 骨架搭建（本次）

- [x] 设计文档定稿 (DESIGN-knowledge-graph-v2.md)
- [ ] 创建 `knowledge/graph/` 目录
- [ ] 创建 `graph/_template.kv` 条目模板
- [ ] 创建 `graph/principles.kv` 原则库
- [ ] 创建 `graph/index.tsv` 主索引（先用 5 个高频条目填充）
- [ ] 创建 `doc/E007.md` 详细文档样例
- [ ] 创建 `graph/E007.kv` 结构化条目样例

### Phase 1: 高频条目改造（后续）

按以下优先级将现有 68 个条目迁移到新结构：

| 优先级 | 条目 | 理由 |
|--------|------|------|
| P0 | E007, E001, E002, E005, E012 | 已有 auto_fix，立即受益于原则过滤 |
| P0 | E064, E063, E061 | 因果链核心节点，修好一个解决多个 |
| P1 | E008, E009, E046, E047, E051 | 安全机制类，跨模式关联强 |
| P1 | E003, E004, E006, E013-E017 | 常见编译错误 |
| P2 | E021-E049 (剩余 compile 类) | 编译阶段全覆盖 |
| P2 | E050-E068 (剩余 runtime 类) | 运行时阶段全覆盖 |

### Phase 2: 引擎替换（后续）

- match_error_pattern() v3 重写，消费 graph/ 数据
- 保留 v2 作为 fallback（如果 graph/ 不存在则降级到旧逻辑）
- 逐步移除硬编码关键词和 case 分支

### Phase 3: 清理（后续）

- 旧 `error-patterns*.md` 标记为 deprecated
- `error-patterns.md` 导航页改为指向 graph/ + doc/
- AI 读写知识库时的默认入口改为 graph/*.kv

---

## §9 对 E007 场景的端到端效果验证

### 9.1 旧流程 (v1/v2) — 失败路径

```
gzip 1.13 configure 失败
日志: "cannot guess build type"
  → v2 引擎: 索引表关键词匹配 → E007 最高分 ✓
  → 加载 error-patterns-core.md
  → _ep_parse_fix() 扫描解决方案段:
    │ grep export → 空
    │ grep ./configure → 空
    │ grep curl config.guess → 空 (因为正文写的是 patch-autotools-ohos.pl)
  → 匹配失败
  → (实际: 回落到更早版本的硬编码 case → 输出 --build= ❌❌❌)
```

### 9.2 新流程 (v3) — 正确路径

```
gzip 1.13 configure 失败
日志: "cannot guess build type"

Phase A: scan index.tsv
  E007 行: keywords="config.guess,build type,HarmonyOS,..."
  grep -qF "cannot guess" → 命中 3 个关键词
  raw_score = 3 × severity(2) = 6

Phase B: 精排
  加载 graph/E007.kv
  error_signature: "cannot guess build type|unable to guess..."
  正则匹配日志 → signature_bonus = +5
  trigger_tool=configure, 当前步骤=configure → phase_bonus = +3
  total = 6 + 5 + 3 = 14 → 远高于其他候选 ✓

Phase C: 方案生成
  rec_approach = download-gnuconfig
  rec_auto_fix = true
  rec_impl = download-gnuconfig
  forbid_1_pattern = "--build=*|--host=*"
  forbid_1_auto_reject = true
  principles = P-AUTOTOOLS-001, P-AUTOTOOLS-002

Phase D: 原则过滤
  检查当前方案 "download-gnuconfig" 是否匹配 forbid_1_pattern:
  → "download-gnuconfig" !~ "--build=*|--host=*" → 通过 ✓
  检查 P-AUTOTOOLS-001 的 forbid_patterns:
  → 同上 → 通过 ✓

Phase E: 输出 & 执行
  → 🧠 知识库命中: E007 (评分:14)
  → 显示 doc/E007.md 内容
  → 🔧 自动修复: download-gnuconfig (通过原则检查)
  → 调用内置 download-gnuconfig 实现:
      curl config.guess → curl config.sub → chmod +x
  → 重试 configure → 成功 ✓✓✓
```

**差异总结**:

| 维度 | 旧(v2) | 新(v3) |
|------|--------|--------|
| 方案来源 | Markdown 代码块（自由文本） | KV 字段 `rec_approach`（结构化） |
| 禁止策略 | 正文中的 ⚠️ 注释（引擎看不到） | `forbid_*` 字段（引擎强制检查） |
| 格式一致性 | 每条目不同 | 模板保证一致 |
| 新增条目成本 | 写 Markdown + 改引擎 case | 写 .kv 文件即可（无需改引擎） |
| 原则检查 | 无 | 强制执行 |

---

*v2 architecture · 2026-04-09*
*下一步: 创建 graph/ 骨架文件 + E007 样例*
