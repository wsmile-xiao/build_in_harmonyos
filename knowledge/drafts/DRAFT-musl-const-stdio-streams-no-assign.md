# DRAFT-musl-const-stdio-streams-no-assign

> musl 将 stdin/stdout/stderr 声明为 `FILE *const`，对标准流赋值在 OHOS 上必然编译失败；freopen 重关联应直接调用、不回赋返回值。

- 状态：草稿（Curator 判定产出，未审核；最终编号 Exxx 由知识库主编确认）
- 申报域：**musl/libc 与 glibc 差异**（八分类之一；兼属编译错误类）
- 机理分层：**L1 平台语义层**（musl 头文件声明语义；单库申报，复发面由 musl 平台本身保证）
- 阻塞面：**编译失败**（硬错误，命中常见阻塞面判据）
- 来源：didiwiki/3.0.5 run（`patches/0002-fix-stdin-const-assign.patch` 所代表问题域）

## 问题特征（真实失败证据）

- 真机编译硬失败（`builder/ci-run-5.log:264-271`）：
  `src/ci.c:181:17: error: cannot assign to variable 'stdin' with const-qualified type 'FILE *const' (aka 'struct _IO_FILE *const')`
  编译器注明 `.../sysroot/usr/include/stdio.h:62:20: note: variable 'stdin' declared const here` → `extern FILE *const stdin;`
- 下游连锁：`ci.o` Error 1 → all-recursive Error 1 → make Error 2 → conan build 失败 → CI 第 5 轮 FAIL。

## 根因（完整因果机理链）

1. **工具实现证据**：OHOS SDK musl sysroot `stdio.h:62-64` 将三条标准流声明为 `extern FILE *const stdin/stdout/stderr;`（musl 刻意把标准流对象指针定为 const 只读，禁止程序重绑定）；glibc 的 `stdio.h` 声明为非 const `extern FILE *stdin;`。
2. **触发命令**：make 编译含 `stdin = freopen(NULL,"r",stdin);` 的源文件（didiwiki 3.0.5 `src/ci.c:181`，`-t` 交互分支清空行缓冲的老式惯用法）。
3. **失败点**：clang 对 const 变量赋值报硬错误（非 warning，无编译开关可关）→ 目标文件失败 → 构建失败。
4. **归类**：musl/glibc 头文件声明语义差异 → 编译失败类。
5. **修复语义依据**：POSIX 规定 freopen 关闭并重关联该流；musl/glibc 的 freopen 均在**原 FILE 对象上就地重关联**并返回其指针，原代码回赋等于把同一指针写回，纯冗余——删除赋值后**全平台行为不变**（非平台 hack）。

## 修复方案（rec）

1. 删除对标准流的赋值，直接调用 freopen（本 run 落地形态：`patches/0002-fix-stdin-const-assign.patch`，1 行改动）。
2. 落补丁前全库 grep 确认对 stdin/stdout/stderr 的全部赋值点（本库仅 `src/ci.c:181` 一处）。
3. 补丁保持上游代码风格，可向上游提交（P-PATCH-003）。

## 回退方案（fallback，诚实权衡）

- 若上游后续逻辑确实使用重关联后的句柄值（需逐库 grep 确认）：改写为 `FILE *reopened = freopen(NULL,"r",stdin); (void)reopened;` 局部承接。权衡：仅当后续代码使用该值才有意义，属等价改写而非功能回退；不改全局变量、不触碰平台头文件。

## 禁止策略（forbid）

- **禁止**修改 SDK sysroot 头文件去掉 const，或用 `#define stdin ...` 宏重定义绕过。
  reason：头文件/宏方案污染所有包含 stdio.h 的翻译单元，破坏环境完整性与可复现性。
  consequence：平台头文件被改后其他所有包的编译行为不可控；SDK 升级后改动失效、问题静默复发。

## verification_cmd（自包含，Curator 2026-09-10 已在设备实测）

```sh
# (1) 工具实现证据：musl sysroot 标准流 const 声明
grep -n 'extern FILE \*const' /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/stdio.h
# → 62:extern FILE *const stdin;  63:extern FILE *const stdout;  64:extern FILE *const stderr;

# (2) 定向复现：对标准流赋值 → 必现硬错误
printf '#include <stdio.h>\nint main(void){stdin = 0; return 0;}' | /data/service/hnp/bin/clang -x c - -o /dev/null
# → error: cannot assign to variable 'stdin' with const-qualified type 'FILE *const'

# (3) 修复形态验证：直接调用 freopen 不回赋 → 编译干净
printf '#include <stdio.h>\nint main(void){freopen(NULL,"r",stdin); return 0;}' | /data/service/hnp/bin/clang -x c - -o /dev/null && echo OK
# → OK（退出码 0）
```

> path-update 阶段复核记录：2026-09-10 Builder 在 ohpc2 真机复验三段探针，输出与上方固化内容完全一致（段 1 命中 stdio.h:62-64 三行；段 2 同一 error 行、clang 退出码 1；段 3 输出 `COMPILE_OK`）。

## 知识沉淀价值

- **可复用问题类别**：musl 标准流 const 声明 × 老式 `stdin = freopen/fdopen` 惯用法的冲突。该惯用法在仅测过 glibc 的老代码中常见（清缓冲、重定向、交互分支），属于"只在 glibc 编译过的 C 代码"迁移到 musl 平台的必踩面。
- **适用库/构建链**：任何 C/C++ 库 + autotools/CMake/raw makefile + OHOS clang/musl 工具链；与构建系统无关。
- **对未来诊断的改进**：日志见 `cannot assign to variable 'stdin'` 即可秒判根因并定位到源码赋值点，避免朝"平台缺符号/头文件缺失"方向误诊。
- **为何不是一次性补丁**：机理在 musl 头文件（平台侧），复发面由平台保证；修复语义（freopen 就地重关联）有 POSIX 依据，跨库通用。

## 确认去重证据（实际检查范围、检索词、命令与逐项差异）

- 检查范围：设备 baseline 仓 `knowledge/graph/`（含 index.tsv、`knowledge/doc/` 全量）、`knowledge/drafts/`（987 个文件）、`knowledge/principles.yaml`、`knowledge/musl-glibc-developer-impact.md`、`knowledge/musl-glibc-full-comparison-iso-posix.md`、`knowledge/musl-glibc-full-comparison-gnu-linux.md`、`knowledge/musl-compat.md`；共享经验仓 `ophs_ci_review/` 全目录（含 .git 之外的全部条目）。
- 检索词与命令（设备端 grep，2026-09-10）：`grep -rli 'stdin' knowledge/`；`grep -rn 'FILE \*const|cannot assign to variable|assign.*stdin|stdin.*assign' knowledge/`；`grep -rli 'freopen' knowledge/`；`grep -rln 'stdin' /storage/Users/currentUser/ophs_ci_review/`。
- 命中与逐项差异：
  - `knowledge/musl-glibc-full-comparison-iso-posix.md:409-411` 仅把 stdin/stdout/stderr 列为"✅ 三平台兼容"，**未记录 const 声明差异**——本条是该对照文档的缺口补注。
  - graph 提及 stdin 的 E076/E082/E093/E133/E161/E214 逐一核对标题与错误特征：分别为 patch-fstat、configure-twice、getpass 缺符号、musl 头文件冲突（nullptr_t/pthread_cond_clockwait）、管道 Permission denied、shell read 阻塞——**均非标准流 const 赋值编译错误**。
  - `FILE *const` / `cannot assign to variable` / freopen 赋值惯用法在 knowledge/ 与经验仓**零命中**。
- 结论：现有知识库与本 run 经验仓均无覆盖，本条为新增知识，非重复申报。

## 适用判断

- 适用：OHOS/musl 编译报 `cannot assign to variable '(stdin|stdout|stderr)' with const-qualified type`，或源码审计发现对标准流赋值。
- 不适用：glibc 平台同名代码（可编译，但建议同样清理）、流重定向到真实新 FILE 且后续使用句柄的场景（用 fallback 形态）、缺符号/隐式声明类问题（分流 E093 等）。
