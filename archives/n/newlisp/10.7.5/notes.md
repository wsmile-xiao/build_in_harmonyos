# newlisp 10.7.5 HarmonyOS PC 适配笔记

## 适配概要

newLISP 10.7.5 是纯 C 单体解释器，构建路线为 `./configure-alt`（非交互，Homebrew 同路线）→ 生成 `makefile_build` → `make`。无第三方运行时依赖。本次适配完成 arm64(OHOS) 静态构建、上游测试实跑分层、消费者冒烟验证。

## 关键决策

| # | 决策 | 说明 |
|---|------|------|
| 1 | 源码镜像源 | 官方 www.newlisp.org DNS 不可达，改用 MacPorts distfile 镜像，sha256 与 Homebrew 公开值字节一致 |
| 2 | 关闭 readline / ffi | 构建开关解决：`--disable-readline --disable-ffi`，不链接 readline/ncurses/libffi，不打补丁 |
| 3 | 静态链接 + 禁用 strip | 设备 exec 沙箱实测只接受静态且未 strip 的 ELF（动态或 stripped ELF 均 EACCES），`--enable-static` + `STRIP= true` |
| 4 | 测试分层 | 上游 make check 独立实跑记录（12 项 11 过）；不集成进 conan create（qa-dot semaphore 平台限制中止会拖挂 CI）；test_package 做消费者冒烟断言 |

## 问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./configure-alt` 直接退出 "Could not discover your OS platform" | uname 返回 "HarmonyOS"，不在 case 分支中 | 0001 补丁：`HarmonyOS) true ${os_type:=LINUX} ;;` |
| 2 | `(pipe)` 调用即崩溃（bash 报 RT42，rc=170） | `p_pipe()` 写端 `fdopen(handles[0], "w")` 误用读端句柄（真实上游 bug，应为 handles[1]），设备 musl libc 触发 SIGRT42 | 0002 补丁：写端改为 `fdopen(handles[1], "w")` |
| 3 | 构建产物 `./newlisp -e '(+ 1 2)'` Permission denied (rc=126) | 动态链接 ELF 或 llvm-strip 后 ELF 被 HarmonyOS exec 沙箱拒绝 | 静态链接（--enable-static）+ 构建时 `STRIP= true` |
| 4 | qa-dot 在 semaphore 处中止 rc=159 "Bad system call" | System V IPC(semget/semop) 被设备 seccomp 拦截（SIGSYS） | 记录为平台限制失败；semaphore 之前所有 built-in 函数测试通过（含 pipe/process/net-*/exec/fork），其余 11 项测试全过 |
| 5 | configure-alt 探测程序执行失败风险 | 探测编译的 test 程序若动态链接则不能 exec | 实测本机 configure-alt 5 项探测全部成功（clang 默认输出未被 strip，可 exec）；无 NEWLISP64 缺失风险 |

## 上游测试实跑

环境：HarmonyOS localhost aarch64，静态未 strip build。

`make check`（Makefile check 目标，12 项逐一实跑）：

| 测试脚本 | rc | 结果 |
|---|---|---|
| qa-dot | 159 | 平台限制失败（semaphore：System V IPC 被沙箱 SIGSYS；此前全部函数通过） |
| qa-dictionary | 0 | Dictionary API tested SUCCESSFUL |
| qa-xml | 0 | XML API tested SUCCESSFUL |
| qa-json | 0 | JSON translation tested SUCESSFUL |
| qa-setsig | 0 | Signal testing SUCCESSFUL |
| qa-net | 0 | Network eval and network file functions IPv4 SUCCESSFUL |
| qa-cilk | 0 | Cilk API tested SUCCESSFUL |
| qa-ref | 0 | Reference testing SUCCESSFUL |
| qa-message | 0 | Message API tested SUCCESSFUL |
| qa-win-dll | 0 | （Windows 限定，自动跳过） |
| qa-bigint 10000 | 0 | big ints tested SUCCESSFUL |
| qa-bench | 0 | Benchmarking all non I/O primitives SUCCESSFUL |

合计：12 项中 11 项通过；qa-dot 因平台限制在 semaphore 处中止（不视为代码缺陷）。

## 消费者冒烟

```bash
$ ./newlisp -e '(+ 1 2)'      # → 3 (rc=0)
$ ./newlisp -v                # → newLISP v.10.7.5 64-bit on Linux IPv4/6 UTF-8. (rc=0)
```

test_package（ctest）：test_newlisp 断言 arith=3 与 version=10.7.5。

## 编译日志

- configure：`/storage/Users/currentUser/tmp/newlisp-configure-final.log`
- build：`/storage/Users/currentUser/tmp/newlisp-build-final.log`
- make check 全量：`/storage/Users/currentUser/tmp/final-makecheck.log`；逐项 `/storage/Users/currentUser/tmp/rc_*.log`

## 许可证

GPL-3.0-or-later（README 声明）。

## 编译结束：2026-09-10
## 最终状态：built（待 CI 验证）