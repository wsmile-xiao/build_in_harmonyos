# agetty 2.42.2 编译笔记（util-linux 2.42.2 组件）

## 编译日期
2026-08-05

## 编译状态
built（本地编译成功，待分析端复核）

## 编译目标
只编译 agetty（util-linux 2.42.2 的 term-utils/agetty.c），通过
`--disable-all-programs --enable-agetty` 禁用其他工具。

## 配置参数
```bash
./configure --disable-all-programs --enable-agetty \
  --disable-nls --disable-rpath --disable-plymouth_support \
  --build=aarch64-unknown-linux-gnu --host=aarch64-linux-ohos
```

## 遇到的问题

### 1. config.guess 无法识别 HarmonyOS（E007）
**错误**: `configure: error: cannot guess build type`
**解决**: `patches/0001-config-guess-ohos.patch`（config.guess 增加 HarmonyOS 分支，
输出 aarch64-unknown-linux-ohos）

### 2. config.status mktemp 临时目录 HMDFS 不可写（既有条目 E011/E052/E060）
**错误**: `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied`
**原因**: HMDFS 上 `mktemp -d` 创建的 0700 目录属主不可写（安全模型差异）
**解决**: `patches/0002-configure-mktemp-hmdfs.patch`（改用 `$TMPDIR/conf$$` + `mkdir -p`）

### 3. linux/socket.h vs sys/socket.h 重定义 sockaddr_storage（E119）
**错误**: `error: redefinition of 'sockaddr_storage'`
**解决**: 编译期 `-D__MUSL__`（conanfile.py，仅 OHOS）

### 4. OHOS libc 缺失 GNU utmpx 符号（E121）
**错误**: `ld.lld: undefined symbol: updwtmpx/setutxent/getutxent/pututxline/endutxent/utmpxname`；
`configure: error: agetty selected, but required GNU utmpx functions not available`
**解决**: `src/ohos-utmpx-shim.c` no-op 降级（仅 OHOS 链接）
**降级边界**: utmp/wtmp 记录不落盘（不声称已写入）；agetty 核心功能（打开 tty、登录提示、调用 login）不受影响

### 5. vhangup 无声明/无导出（路径 B 候选，待分析端确认）
**错误**: `warning: call to undeclared function 'vhangup'` + `ld.lld: error: undefined symbol: vhangup`
**证据**: SDK `ohos-sdk_26.0.0.18` sysroot 头文件无 vhangup 声明；libc.so 无导出符号
**解决**: `src/ohos-utmpx-shim.c` 使用 AArch64 `SYS_vhangup`（__NR_vhangup=58）syscall 封装
**矛盾**: knowledge/musl-glibc-full-comparison-iso-posix.md 记录 vhangup 三 libc 均可用，
与 OHOS 26.0.0.18 实测不符；以实测诊断为准，待分析端判定

## 安装验证

### 关键产物
- `bin/agetty`（154KB，aarch64 PIE，仅依赖 libc.so）

### 消费者测试（test_package）
- `agetty --version` → `agetty from util-linux 2.42.2`（退出码 0 + 版本字符串断言）
- `agetty --help` → 退出码 0（不打开真实 TTY）
- 2/2 PASS（conan create test_package 真实执行）

## 上游测试
`0/0 (N/A，无 agetty 适用的上游测试)`——完整枚举依据见 manifest.yaml

## 知识提取
- vhangup 缺失为 E121 未覆盖的独立符号候选（待分析端确认后决定是否生成草稿）

---
*编译完成时间: 2026-08-05*
---

**编译结束**: 2026-08-05 20:27
**最终状态**: built
