# DRAFT-util-linux-login-2.42.2-ohos-musl-pam-portability

## 问题

`util-linux-login/2.42.2` 在 OHOS `aarch64` CI 上不是单一错误，而是一条
从依赖探测到链接的兼容性链：

- configure 找不到 Conan 依赖 `linux-pam/1.7.2` 提供的
  `security/pam_appl.h`；
  - OHOS musl 不导出 GNU utmpx 函数实现，链接阶段报
  `getutxent/getutxid/getutxline/pututxline/setutxent/endutxent/utmpxname`
  未定义；
  - OHOS musl 无 `vhangup`；
  - `getusershell/setusershell/endusershell` 既无声明也无实现，且
  `login.c` 的项目头文件包含路径与调用路径不一致；
  - kernel.org 主源地址在 CI worker 上偶发读超时。

PR #7031 最终在 CI #37390 通过 Conan build、`test_package`、L0 和 L1。

## 根因

### PAM 探测

`AC_CHECK_HEADERS` 的预处理探测读取的是 `CPPFLAGS`。手工把 Conan 包的
include 目录只加进 `CFLAGS` 时，编译常规源文件可以看见头文件，但 configure
的头文件探测仍失败。`AutotoolsDeps(self).generate()` 会把
`linux-pam/1.7.2` 的 include/library 路径导出到 autotools 环境，使
`security/pam_appl.h`、`security/pam_misc.h` 和 PAM 库在探测与链接两个阶段
都可见。

### utmpx 与 vhangup

OHOS musl 有 utmpx 类型与声明，但本 CI 环境未提供上述 GNU utmpx 函数实现；
只补原型会让错误后移到链接期。`vhangup` 同样缺少 libc 符号。最终补丁在
`login.c` 中以 `#if !defined(__GLIBC__)` 定义 no-op stub，并在 configure 层
允许 login 在无 GNU utmpx 扩展时继续构建；所有 `updwtmpx` 调用均由
`HAVE_UPDWTMPX` 保护。

不要用 `__OHOS__` 作为条件。CI 已确认该目标 clang 未定义 `__OHOS__`，导致
兼容代码被静默跳过；`!__GLIBC__` 能覆盖 OHOS musl，同时保留 glibc 的真实
实现。

### getusershell

OHOS musl 不提供 `getusershell` 系列。`lib/shells.c` 中的 stub 定义本身不够：
`login.c` 只有在 `HAVE_LIBECONF && USE_VENDORDIR` 成立时才包含 `shells.h`，
而 OHOS 配置禁用了该路径。因此 `login.c` 调用处必须直接看见正确的
`char *getusershell(void)` 原型，否则 clang 按隐式 `int` 处理并在赋给
`char *` 时触发 `-Wint-conversion` 硬错误。

最终结构是：`include/shells.h` 为非 glibc 消费者声明三个原型，
`lib/shells.c` 提供 `getusershell() == NULL` 的降级实现；针对 login 的
条件包含缺口，`login.c` 内也保留原型。返回 `NULL` 表示本项目未提供额外
已知 shell，不修改测试断言。

## 方案

1. 保持聚焦包边界：`--disable-all-programs` 后仅
   `--enable-login --enable-nologin`，输出 Conan application，而不是把完整
   util-linux 工具集引入包依赖面。
2. `requirements()` 声明 `linux-pam/1.7.2`，并在 toolchain 生成后调用
   `AutotoolsDeps(self).generate()`，让 PAM 路径进入 configure/link 环境。
3. `configure` 允许 login 在无 GNU utmpx 扩展时构建；`updwtmpx` 全部按
   `HAVE_UPDWTMPX` 保护。
4. 在 `login.c` 用 `!__GLIBC__` 定义 OHOS musl 缺失的七个 utmpx 函数与
   `vhangup` no-op 链接 stub。
5. 在 `include/shells.h` 声明 getusershell 系列，在 `lib/shells.c` 提供降级
   定义，并在 `login.c` 的条件包含缺口处补原型。
6. 保留官方 tarball SHA256，主 URL 失败时依次尝试 kernel.org 镜像；镜像只
   改下载来源，不改校验值。

## 验证

- CI #37390：`ohos-aarch64` 上 Conan build、`test_package`、L0、L1 均通过。
- 包级冒烟断言：2/2，覆盖 `login` 与 `nologin` 两个产物的存在、可执行和
  help 启动语义。
- 上游包级测试：0/0，不适用。上游没有随该聚焦 Conan 包执行的
  login/nologin 单程序测试；不得把 0/0 写成 100%，也不能引用无关套件数字。
- 交互式登录运行边界：仍需 `/etc/pam.d/login`、真实终端和适当权限/SUID
  设置。CI 验证的是构建与包产物可用性，不伪造完整登录行为。

## 与既有条目的差异

- E245：记录 libc 缺 `vhangup` 但内核 syscall 可用时应使用
  `syscall(SYS_vhangup)` 并保留真实失败语义。本条记录的是 CI 聚焦包中
  让 login 链接通过的 no-op 边界；若要恢复真实终端 hangup 行为，应回退到
  E245 的 syscall 方案。
- E534：覆盖 musl 缺 `getusershell` 等 GNU/BSD 扩展的通用缺函数模式。本条
  新增 util-linux 2.42.2 的具体陷阱：`login.c` 条件包含 `shells.h`，所以
  `lib/shells.c` 的定义不会自动向调用点暴露原型。
- E467：提醒 AutotoolsDeps 可能把整条共享依赖闭包带入早期探测。本条是它的
  PAM 头文件正例：该应用需要通过 CPPFLAGS/LDFLAGS 暴露 linux-pam，且最终
  CI 证明该方式在本包可行。

## 适用边界

- 适用：OHOS musl 上构建聚焦的 util-linux 程序子包，尤其是依赖 Conan PAM
  且需要跨越 configure/header/link 三层的 autotools 应用。
- 不适用：完整交互式登录验收、需要真实 utmp/wtmp/btmp 审计语义的服务，或
  必须执行 vhangup 副作用的终端程序。
- 恢复条件：若平台后续导出这些 libc API，应删除对应 no-op stub 并优先使用
  系统实现；涉及真实 vhangup 语义时按 E245 使用 syscall 并保留错误返回。
