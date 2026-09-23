# musl features.h 不隐式定义 _POSIX_C_SOURCE，上游以 defined(_POSIX_C_SOURCE) 判定 POSIX 系统的探测会落 #error Unknown system，应补 __linux__/__unix__ 族宏或改能力探测

- draft: musl-no-implicit-posix-c-source（与同 slug 的 `.kv` 并置；不自行编号 Exxx）
- status: pending-editor-review
- 八分类归属：musl/libc 与 toybox 差异（检索面双挂 musl-libc / platform-detect 关键词）
- severity: 2 ｜ phase: compilation ｜ trigger_tool: clang|clang++|cmake|make
- 适配实例: coin 4.0.10 上游 CoinTests harness（TestSuiteUtils.cpp:37/42，2026-09-10）

## 机理

glibc features.h 在默认（gnu）方言、未显式指定特性宏时，经隐式 _DEFAULT_SOURCE 将 _POSIX_C_SOURCE 定义为 200809L（glibc ≥2.19，feature_macros(7)）；musl features.h 只消费用户提供的特性宏、从不自行定义，且 clang 对任何目标 libc 均不预定义 _POSIX_C_SOURCE。因此上游"以 defined(_POSIX_C_SOURCE) 当 POSIX 系统探测器"的代码（典型：#if defined(_POSIX_C_SOURCE)…#define USE_POSIX … #elif defined(_WIN32) … #else #error Unknown system）在 glibc/Linux 恒真，在 musl/OHOS 恒假，落入 #else 分支 #error，库或测试 harness 构建失败。OHOS clang 实证（-E -dM）：__linux__/__unix__/__OHOS__ 均预定义为 1，__MUSL__ 不定义，_POSIX_C_SOURCE 含 features.h 后仍未定义。

glibc / musl 对照：

| 事项 | glibc | musl/OHOS |
|---|---|---|
| features.h 对 _POSIX_C_SOURCE 的默认处理 | 默认（gnu）方言下经隐式 _DEFAULT_SOURCE 定义为 200809L（≥2.19，feature_macros(7)） | 只消费用户提供的特性宏，从不定义 |
| clang 是否预定义 _POSIX_C_SOURCE | 否（对任何目标 libc 均不预定义） | 否 |
| __linux__ / __unix__ | 预定义为 1 | 预定义为 1（另 __OHOS__ 预定义为 1） |
| __MUSL__ | —（glibc 侧不适用） | 不定义（OHOS clang 15 -E -dM 实证） |
| defined(_POSIX_C_SOURCE) 探测结果 | 恒真（探测缺陷被遮蔽） | 恒假 → 落 #else 分支 #error Unknown system |

## 识别

- error_signature: `#error Unknown system|#error.*[Uu]nknown.*system`
- match_keywords: _POSIX_C_SOURCE, _POSIX_SOURCE, USE_POSIX, Unknown system, features.h, 特性宏, 平台探测, musl, glibc 默认定义, __linux__, feature test macro
- 典型形态（上游探测模板）：

```
#if defined (_POSIX_C_SOURCE) || defined (_POSIX_SOURCE) || defined(__APPLE__) || defined(__FreeBSD__)
#define USE_POSIX
#elif defined(_WIN32)
#define USE_WIN32
#else
#error Unknown system
#endif
```

## 方案空间

### 推荐（rec_priority: 1 — extend-probe-with-linux-family-macro）

在上游探测链追加 `|| defined(__linux__)`（或更泛 `|| defined(__unix__)`），保留原有分支与 #error 兜底。进配方的改动走 conandata 补丁并带完整元数据（P-PATCH-004）；若改动仅服务上游测试门禁 harness 且配方 COIN_BUILD_TESTS=OFF 不构建测试（coin 4.0.10 案例），则改动保留在门禁构建树、不进配方交付物，并留 pristine A/B 反证日志。

参考实现：`#if defined (_POSIX_C_SOURCE) || defined (_POSIX_SOURCE) || defined(__APPLE__) || defined(__FreeBSD__) || defined(__linux__)`；验证=探针②③；门禁场景另留 pristine 构建失败日志与 diff 证明唯一差异。（rec_auto_fix: false；rec_impl: patch-upstream-or-gate-harness-only）

### fallback（fallback_priority: 2 — define-posix-c-source-via-cxxflags）

无法改源时以 `-D_POSIX_C_SOURCE=200809L`（CXXFLAGS/CMake add_compile_definitions）使 defined() 为真。掩盖探测语义而非修复：改变整个翻译单元的可见性集合，可能与上游其他探测交互；须按 P006 记录技术债。注意：改用 -std=gnu 方言只对"声明门控"类近亲问题（capstone 类，E152 族）有效，对本探测（musl 任何方言都不定义该宏）无效。（fallback_auto_fix: false）

### 禁止（forbid）

1. `删除 #error 分支｜直接 #define USE_POSIX` — 破坏上游平台判定完整性，丢失 _WIN32 分支选择语义，探测退化为盲断；跨平台回归风险，上游不可收。
2. `把 POSIX 族判定改写为 #ifdef __OHOS__` — 将"是否 POSIX 系统"的能力族探测降级为平台名硬编码（态度审计①），且不可向上游提交（P005）；__OHOS__ 只用于 OHOS 专属行为隔离（P004 边界）。后果：上游拒收；非 OHOS 的 musl 平台仍坏。
3. `依赖 __MUSL__ 判定 musl` — OHOS clang 15 实证（-E -dM）不预定义 __MUSL__；判定恒假，误判平台。

## 自包含验证（探针，任意目录新 shell 可跑，零落盘）

① 工具实现证据：musl 不回显特性宏；glibc 机器上运行同命令应得 ECHO_POSIX_DEFINED（glibc 侧另见 feature_macros(7)）：

```
printf '#include <features.h>\n#ifdef _POSIX_C_SOURCE\nECHO_POSIX_DEFINED\n#else\nNO_POSIX_MACRO_ON_MUSL\n#endif\n' | clang -E -x c - | grep POSIX_MACRO
```

期望（OHOS/musl）: NO_POSIX_MACRO_ON_MUSL

② 定向复现：上游式平台探测构建失败：

```
printf '#if defined(_POSIX_C_SOURCE) || defined(_POSIX_SOURCE) || defined(__APPLE__) || defined(__FreeBSD__)\n#define USE_POSIX\n#elif defined(_WIN32)\n#define USE_WIN32\n#else\n#error Unknown system\n#endif\nint x;\n' | clang -fsyntax-only -x c -
```

期望: error: Unknown system

③ 修复验证：探测链补 __linux__ 族宏后通过：

```
printf '#if defined(_POSIX_C_SOURCE) || defined(_POSIX_SOURCE) || defined(__APPLE__) || defined(__FreeBSD__) || defined(__linux__)\n#define USE_POSIX\n#elif defined(_WIN32)\n#define USE_WIN32\n#else\n#error Unknown system\n#endif\nint x;\n' | clang -fsyntax-only -x c -
```

期望: 无输出（通过）

注：glibc 侧机理为文档引证（feature_macros(7)），设备（OHOS/musl）无 glibc 对照。

## 案例：coin 4.0.10 CoinTests harness

- 上游探测链（pristine tarball）`testsuite/TestSuiteUtils.cpp:37`：`#if defined (_POSIX_C_SOURCE) || defined (_POSIX_SOURCE) || defined(__APPLE__) || defined(__FreeBSD__)` → `#else` `#error Unknown system`（:42）。库本体 src/ 无此模式、可独立构建（配方零补丁，CI 一次通过）；仅测试 harness 命中。
- 修复：该行补 `|| defined(__linux__)`（全树唯一源码差异），门禁构建树内保留、不进配方（COIN_BUILD_TESTS=OFF）。
- 结果：pristine 构建失败（#error Unknown system，7 errors）→ 修复后官方 CoinTests 真机全量 325/325、83466 checks、exit 0（三轮一致）。
- 证据（run coin-4.0.10 设备临时目录 /storage/Users/currentUser/tmp/oh-device-porting-v2/coin-4.0.10/，run 收口后可能清理）：
  - `cointests_pristine_build.log` — pristine A/B 反证（TestSuiteUtils.cpp:42 error: Unknown system）
  - `verify_src_diff_final.txt` — 全树 vs tarball 唯一差异证明（11 行，仅此一处）
  - `cointests_run3_gate.log` — 修复后门禁运行（[OK] 325 tests, 83466 checks + EXIT_CODE=0）
  - `posixmacro.cpp` / `posixmacro` — 宏探针（_POSIX_C_SOURCE 未定义、__linux__ 已定义）

## 关联

- principles: P005（补丁可上游）、P006（CFLAGS hack 记债）、P004（辨析：__OHOS__ 属平台隔离场景，非本探测场景）
- similar_to: [E152, E138, E092]
- conflicts_with: []
- 加注建议：既有 musl-glibc-full-comparison-gnu-linux.md §4.3 将 _POSIX_C_SOURCE 标为 glibc✅/musl✅，仅覆盖"宏被尊重"，未覆盖"默认是否定义"；建议知识库主编收录本条时对该行加注。
