# busybox-ohos-musl-gnu-ext — OHOS musl 缺失 GNU/BSD 扩展函数

> **状态：** `draft: true`  
> **来源：** BusyBox 1.36.1 R01 本地适配，OHOS 平台  
> **验证对象：** busybox/1.36.1 (conan create, sign-elf, clean CONAN_HOME install, test_package)  
> **关联条目：** E093 (musl 缺 getpass), E213 (musl 缺 l64a), E094 (musl 缺 pthread_attr_setaffinity_np)  
> **非重复声明：** 本条目验证的具体函数(gethostid/strverscmp/sigisemptyset/getusershell)未被任何已有正式条目或草稿覆盖。

## 问题

OHOS 的 musl libc 实现与 glibc 相比，缺少若干 GNU/BSD 扩展函数。BusyBox 1.36.1 在 OHOS 上编译时，以下函数导致编译/链接失败：

| 函数 | 所属 applet | 影响 | 修复方式 |
|------|-------------|------|----------|
| `gethostid()` | `hostid` | 链接未定义 | missing_syscalls.c 兼容实现 |
| `strverscmp()` | `sort -V`, `ls -v` | 链接未定义 | missing_syscalls.c 兼容实现 |
| `sigisemptyset()` | `hush` shell | 链接未定义 | missing_syscalls.c 兼容实现 |
| `getusershell()` | `su` | 编译错误（隐式声明→Werror 风格） | 禁用 CONFIG_SU |

## 根因

OHOS musl libc 不实现 gethostid、strverscmp、sigisemptyset、getusershell 等非 POSIX 函数。BusyBox 默认配置（`make defconfig`）启用这些 applet，且 BusyBox 源码中 `HAVE_STRVERSCMP` 被硬编码为 1 而无 musl 检测，导致编译期条件判断错误。

## 修复方案

### 方案 A（推荐）：weak 弱符号兼容补丁 + 配置禁用

向 `libbb/missing_syscalls.c` 添加 `__attribute__((weak))` 弱符号兼容实现（无需平台条件编译，链接时自动检测：glibc 强符号优先，musl 缺时弱定义生效）：

```c
// 使用 weak 弱符号，链接时自动检测 libc 是否提供该函数
__attribute__((weak)) long gethostid(void) { return 0; }
__attribute__((weak)) int strverscmp(const char *s1, const char *s2) { ... }
__attribute__((weak)) int sigisemptyset(const sigset_t *set) { ... }
```

因 `getusershell()` 需要读取 `/etc/shells`（OHOS 无此文件），直接禁用 `CONFIG_SU=n`。

完整补丁文件见 `patches/0001-ohos-compat-missing-libc-functions.patch`。

### 方案 B（备选）：完全禁用调用 applet

- `CONFIG_HOSTID=n` — 禁用 hostid 命令
- `CONFIG_FEATURE_SORT_BIG=n` — 禁用 sort -V（版本排序）
- `CONFIG_SU=n` — 禁用 su 命令
- `CONFIG_HUSH=n` — 不可行，hush 是 BusyBox 默认 shell，禁用影响核心功能

## 验证

1. `conan create` 编译+链接通过（无未定义符号错误；weak 弱符号对 glibc 强符号无影响）
2. `ld.lld` 链接阶段错误消失（weak 定义在 musl 上绑定，在 glibc 上被强符号覆盖）
3. `test_package` 消费者: 签名后可执行时 381 applets 全部通过（`--help`/`--list`/`echo hello`/`true`/`wc -l`）；未签名时返回 SKIP（已知平台限制：sign-elf 为 OHOS 执行前置条件）
4. `sign-elf` 完成
5. W3 本地 CI 验证通过（Pass rate 100.0%，含 L1e 反向依赖验证）

## 适用边界

- **适用:** 基于 musl 的 libc 环境、使用 `gethostid`/`strverscmp`/`sigisemptyset`/`getusershell` 的软件（link-time 弱符号自动检测：glibc 强符号优先，musl 缺时弱定义生效）
- **不适用:** glibc 平台、其他 musl 发行版（如 Alpine Linux ≥ 1.2.3 已提供 strverscmp）
- **已知限制:** gethostid 返回 0 而非读取 /etc/hostid；strverscmp 未处理 locale 排序；getusershell 未提供等价实现（因需 /etc/shells 支持）

## 原始证据

- 构建日志: `/storage/Users/currentUser/tmp/conan-create-busybox.log`
- 补丁文件: `archives/b/busybox/1.36.1/patches/0001-ohos-compat-missing-libc-functions.patch`
- test_package 输出: 381 applets, 5 项烟雾测试全通过（exit code 0）
- 初步报告: `~/.oh-runner/reports/busybox-1.36.1-r01-*.json`