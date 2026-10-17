# DRAFT — OpenHarmony 适配：用构建系统注入能力宏替代源码 OHOS 条件编译宏（getprogname/program_invocation_name → /proc/self/exe）

> 对应结构化数据：`knowledge/drafts/DRAFT-mesa-24.3.4-meson-proc-self-exe-feature-macro.kv`
> 触发事件：mesa 24.3.4 HarmonyOS PC 适配（R02/R04 审查返工，PR #7521）
> 验证实例：mesa 24.3.4（OHOS PC aarch64，softpipe 软渲染）

## 1. 知识库名称

**构建系统注入能力宏替代源码 OHOS 条件编译宏（proc/self/exe 进程名）**

## 2. 问题背景

OpenHarmony（HarmonyOS PC）用户空间**不提供** `program_invocation_name` / `getprogname()`，
但提供 linux 风格 `/proc/self/exe`。第三方 C/C++ 库需要获取当前进程名（如 Mesa 的
`util_get_process_name()`，用于 per-app 配置/日志）时，常见做法是在源码里加平台分支：

```c
#if defined(__OHOS__) || defined(__OHOS_FAMILY__)
    /* readlink("/proc/self/exe") … */
#endif
```

这在赛事/项目规则 R8 下是**硬性违规**：源码和 patches 不得引入
`__OHOS__` / `__OHOS_FAMILY__` 平台条件编译宏；平台适配应由构建系统判断，
源码只判断**平台无关的能力宏**。

已遇到的具体实例：mesa 24.3.4 的 `src/util/u_process.c`。

## 3. 问题根因

- 平台事实：OHOS musl libc 无 `program_invocation_name` / `getprogname()`（与 E203 记录一致），
  但 `/proc/self/exe` 可用。
- 违规根因：直接把 `__OHOS__` 宏写进 C 源码/patch，会把平台适配绑定在“宏是否被外部定义”
  这一不可控前提上（取决于编译环境），且违反 R8“一律 request changes”。
- 对比同 PR 内合规做法：`meson.build` 里 `host_machine.system() == 'harmonyos'` 判断
  属于构建系统层，合规。

## 4. 适用范围

适用：
- OHOS / HarmonyOS aarch64（armv8）上需要获取进程名、但 libc 无
  `program_invocation_name`/`getprogname` 的 C/C++ 库。
- 使用 Meson 构建（或等价的 CMake/autotools 构建系统平台判断）的三方库 patch。

不适用：
- 有 `program_invocation_name`/`getprogname` 的平台（glibc/macOS/Android 等），
  走原有分支即可。
- 纯 CMake 项目若无法注入预处理器宏，需等价机制（如 cmake 平台判断 + target_compile_definitions）。

## 5. 输入

- 项目类型：C/C++，构建系统 Meson（本案例）或等价系统。
- 触发点：源码需按平台取进程名 / 其他 libc 能力差异。
- 相关日志/信号：`util_get_process_name` 返回空串、`process_test` 期望与实际不符、
  review 评论“patch 引入 __OHOS__ 违反 R8”。

## 6. 输出

- 构建系统注入的平台无关能力宏，例如 `HAVE_READ_PROC_SELF_EXE`。
- C 源码只判断该能力宏，并用 POSIX 接口（`readlink("/proc/self/exe")`）实现 fallback。
- 进程名测试通过（`util_get_process_name()` 返回真实 basename）。

## 7. 解决方案

1. **meson.build 注入能力宏**（平台判断留在构建系统层）：
   ```meson
   if cc.has_header_symbol('errno.h', 'program_invocation_name',
                           args : '-D_GNU_SOURCE')
      pre_args += '-DHAVE_PROGRAM_INVOCATION_NAME'
   endif
   # HarmonyOS user-space provides /proc/self/exe but no program_invocation_name/getprogname
   if not pre_args.contains('-DHAVE_PROGRAM_INVOCATION_NAME') and host_machine.system() == 'harmonyos'
      pre_args += '-DHAVE_READ_PROC_SELF_EXE'
   endif
   ```
2. **C 源码只判断能力宏**（u_process.c 新增分支，不用 `__OHOS__`）：
   ```c
   #elif defined(HAVE_READ_PROC_SELF_EXE)
   /* 无 program_invocation_name/getprogname 但有 /proc/self/exe 的平台 */
   static char *__getProgramName(void) {
      char path[4096];
      ssize_t len = readlink("/proc/self/exe", path, sizeof(path) - 1);
      if (len <= 0) return strdup("");
      path[len] = '\0';
      char *base = strrchr(path, '/');
      if (base && base[1] != '\0') return strdup(base + 1);
      return strdup(path);
   }
   ```
3. **验证**：`process_test` / 鸿蒙专项测试断言进程名等于二进制 basename。

## 8. 使用方法

1. 在构建系统里按平台注入能力宏（Meson：`host_machine.system()`；CMake 等价：
   `if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS")` + `target_compile_definitions`）。
2. C 代码用能力宏 + POSIX 接口写 fallback，不引用任何 `__OHOS__` 宏。
3. 回归测试：跑进程名相关单测与专项测试，确认 fallback 分支真实生效。

## 9. 示例（mesa 24.3.4）

- 补丁：`archives/m/mesa/24.3.4/patches/0002-meson.build.patch`（注入宏）、
  `patches/0006-src-util-u_process.c.patch`（能力宏分支）。
- commit：`96b2fb963ffe26dcdec320d7c7d07bc1d4ed0dfe`（R03 交付）。
- 验证命令/退出码/日志：
  - `meson setup --reconfigure <build>`，exit 0；
  - `ninja -C <build> src/util/process_test src/gallium/tests/trivial/ohos_adapt_test`，exit 0；
  - `./src/util/process_test`（设 BUILD_FULL_PATH），exit 0；
  - `GALLIUM_PIPE_SEARCH_DIR=<build>/src/gallium/targets/pipe-loader ./ohos_adapt_test`，
    exit 0，`[OHOS] PASS: process name matches binary basename`、
    `OHOS_ADAPT_TEST: ALL PASS`；
  - 补丁内 `__OHOS__`/`__OHOS_FAMILY__` 计数 0（grep）。
- 日志：`archives/m/mesa/24.3.4/reports/` 下 R02/R04 证据日志（含 SHA-256）。

## 10. 通用性说明

不是 mesa 特例补丁，而是一类问题的通用解法：OHOS 平台 libc 能力差异，
应由构建系统注入**平台无关能力宏**，C 源码用能力宏 + POSIX 接口 fallback，
避免 `__OHOS__` 源码宏守卫（R8 合规）。可被任何“需按平台探测 libc 能力”的 C/C++ 库复用。

## 11. 验证结果

- `process_test`：`util_get_process_name()` 返回 `process_test`（exit 0）。
- `ohos_adapt_test`：进程名断言 PASS + softpipe 离屏渲染 4096/4096 非背景像素
  （`OHOS_ADAPT_TEST: ALL PASS`，exit 0）。
- 上游测试 41/43（2 组 OHOS 环境差异，非本知识范畴）；消费者 test_mesa ALL PASS。
- 补丁内 OHOS 条件宏计数 0。

## 12. 与既有知识差异（查重）

- **E203** 已覆盖“OHOS musl 无 getprogname/program_invocation_name”的事实，
  但其 `rec_approach` 是 `#ifdef __OHOS__` 源码守卫方案，且 `forbid` 未覆盖
  “禁止源码宏守卫”这一规则；**本草稿只沉淀 R8 合规的构建系统注入能力宏方案**，
  不复制 E203 的宏守卫方案。E203 保留其 poll.h/include 等其他内容。
- **E002** 覆盖 /tmp 只读/TMPDIR，与本知识无关（候选 TMPDIR 复用 E002，不建草稿）。
- **E017/E185/E066/E150/E195** 覆盖网络/归档/源码包，与本知识无关。

## 13. 结论

OHOS 平台 libc 能力差异（无 program_invocation_name/getprogname）需要按平台 fallback；
赛事规则 R8 禁止源码 `__OHOS__` 条件编译宏。正确做法是**构建系统注入平台无关能力宏 +
C 源码 POSIX fallback**，既满足平台适配又符合 R8。属于可复用通用方案（路径 B）。
