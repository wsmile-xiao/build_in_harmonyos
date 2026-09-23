# DRAFT-ohos-header-exists-but-api-missing-and-tool-presence — 「检测通过」≠「能力可用」

> 配套：procenv 0.51 适配（contrib-9733）。本条沉淀的是**跨项目可复用**的一类问题：
> 在 OHOS 上，autoconf/CMake 的"存在性检测"会因为 **uapi 风格裁剪头**、**HMDFS 临时目录**、
> **缺构建期 CLI 工具**、**第三方库 IPC 机制** 四类原因给出错误结论。

## 错误特征

同一份源码，在 OHOS 上可能出现这几种"检测说 OK、用起来爆炸"的形态：

```
# (1) 头存在但无 API（configure 通过 → 编译失败）
error: unknown type name 'cap_t'
error: unknown type name 'cap_value_t'
error: use of undeclared identifier 'CAP_EFFECTIVE'

# (2) autoconf 临时目录（configure 通过 → config.status 失败）
./config.status[788]: can't create ./conffFGEae/subs1.awk: Permission denied
config.status: error: could not setup config files machinery

# (3) 构建期工具缺失（测试整体失败）
./check_all_args[813]: groff: inaccessible or not found
FAIL: check_all_args

# (4) 依赖库 IPC（测试整体失败，与产品无关）
.../check_msg.c:317: Unable to create temporary file for communication; may not have permissions to do so
FAIL: check_pr_list
```

## 触发条件

- 平台：OHOS（HarmonyOS PC，musl/clang，HMDFS 文件系统）
- 阶段：`configuration`（检测/临时目录）、`compilation`（误启用的可选功能）、`testing`（缺工具/IPC）
- 代码模式：`AC_CHECK_HEADERS` 决定可选功能；autoconf 生成脚本建临时目录；测试脚本调用外部 CLI

## 根因分析（逐项实测）

### (1) `<sys/capability.h>`：头存在 ≠ libcap 可用

```sh
SR=$HOME/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/sysroot
wc -l "$SR/usr/include/sys/capability.h"                                  # 48
grep -cE "cap_t|cap_get_proc|CAP_EFFECTIVE" "$SR/usr/include/sys/capability.h"   # 0
```

OHOS 提供的是 **Huawei 裁剪的、内核 uapi 风格** 的 `<sys/capability.h>`（48 行），
**没有 libcap 的用户态 API**。但 `AC_CHECK_HEADERS([sys/capability.h])` 只看头是否存在 →
**假通过** → 源码里 `#ifdef HAVE_SYS_CAPABILITY_H` 的段被启用 → `unknown type name 'cap_t'`。

对照：上游其实还有 `AC_SEARCH_LIBS([cap_init],[cap])`（函数级检测，会正确判否），
但源码用的是**头宏**而不是它 → 检测与使用不一致。

### (2) autoconf 临时目录 + HMDFS

`configure`/`config.status` 里：

```sh
tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` && test -d "$tmp"
```

在 HMDFS 上用 `077` 建的目录随后写 `subs1.awk` 会 `Permission denied`。
仓库既有先例：**e2fsprogs 0003 补丁**把 `umask 077` 放宽为 `022` 解决。

### (3) 构建/测试期外部 CLI 工具缺失

上游 `check_all_args` 用 `groff -a -man -Tascii` 渲染 man page 做选项交叉校验；
还用到 `xmlwf`/`json_pp`/`locale`。OHOS 全都没有 → 脚本把这些当失败。
正确处理是**工具缺失时 skip 该断言**（保留其余真实用例），而不是删用例或忽略整体失败。

### (4) libcheck 的 fork/IPC：目录优先级陷阱（已解决）

`libcheck 0.15.2` 选择临时目录的顺序是 **`TEMP` > `P_tmpdir`（编译期 "/tmp"）> `TMPDIR` > "."**。
`P_tmpdir` 编译期即 `/tmp`，**优先于 `TMPDIR`**，而 OHOS 的 `/tmp` 只读 →
无论 `TMPDIR=/dev/shm`、构建目录还是 `$HOME/tmp` 都会报
`check_msg.c:317: Unable to create temporary file for communication`。

**解决**：设第一优先级的 `TEMP` 指向可写目录即可：

```sh
TEMP=<writable> LD_LIBRARY_PATH=<check>/lib ./check_pr_list
# -> 100%: Checks: 7, Failures: 0, Errors: 0
```

教训：遇到"改 `TMPDIR` 无效"的临时目录问题，先确认该程序自己的目录优先级
（有些程序把编译期 `P_tmpdir` 放在 `TMPDIR` 之前），必要时改用 `TEMP` 或直接给它一个可写目录。

## 解决方案

1. **把"头存在"升级为"能力存在"**：`AC_SEARCH_LIBS(cap_init, cap)`；若不想改上游，
   在配方里钉 autoconf 缓存变量：`configure ... ac_cv_header_sys_capability_h=no`（可复核、无源码改动）。
2. **autoconf 临时目录**：`patches/0001-configure-relax-umask-for-hmdfs.patch`
   （`umask 077` → `022`；生成文件按 P003 以补丁形式提交）。
3. **构建/测试脚本**：先 `command -v groff/xmlwf/json_pp/locale` 探测，缺失 `msg` + `return 0` 跳过；
   `TMPDIR` 指向构建目录内的可写目录。
4. **依赖级限制如实记录**：`build()` 里用 `timeout` 实跑并把退出码写入日志，报告里单列原因，
   不修改上游判定、不删除用例。
5. **新编译器告警**：按 P007 精准放宽（如 `-Wno-error=unused-but-set-variable`），不全局关 `-Werror`。
6. **守卫用 libc 特性宏，不要用平台宏**：`major/minor`、`pthread_getconcurrency`、
   `pthread_getaffinity_np` 的根因是 **libc（musl vs glibc）** 而非平台名，应写 **`#if !defined(__GLIBC__)`**
   （或配置期探测），**不要** `#ifdef __OHOS__` —— libc 守卫能覆盖所有 musl 发行版，且平台宏会随移植平台膨胀。
   （本 PR 的 AI 检视即把 `#ifdef __OHOS__` 标为 High Priority 要求改写。）
   `getpwuid()` 一例更彻底的做法是**去掉条件编译**：所有平台遇 `errno == 0 && pw == NULL`
   统一按"未知用户"降级（容器/无 passwd 环境同样受益）。

## 验证（procenv 0.51 实测）

```sh
conan create archives/p/procenv/0.51 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
# -> CREATE_EXIT=0
# make check TESTS="tests/show_machine_details check_all_args" -> All 2 tests passed
# timeout 15 procenv（无参数） -> exit=124（忙等，另见第二条草稿/notes）
```

## 查重差异

- **E011** 覆盖的是"umask 077 导致 configure/config.status 失败"这一**单点**；
  本条把它与"头存在但 API 缺失"、"外部工具缺失被当失败"、"依赖 IPC 限制"合并为
  **同一方法论**：*检测通过 ≠ 能力可用*，并给出"升级为能力探测 + 如实降级"的统一处置。
- **E091/E119** 是 `sockaddr_storage` 重定义的具体修法；本条不重复该修法，只在其上引用。

## 元信息

- authors: `frj__`（contributor_id: `frj__`）
- source_event: procenv 0.51 OHOS aarch64 适配（2026-09-16）
- draft: true —— 待主编审核后 promote 为正式 E 条目
