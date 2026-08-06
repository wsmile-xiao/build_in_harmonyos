# DRAFT — OHOS 上 libc 未导出 vhangup 的声明/链接/syscall 分层诊断与 shim 边界

> 库: agetty 2.42.2（util-linux 2.42.2 `term-utils/agetty.c` 组件）
> 状态: draft（用于路径 B 证据审计，**不是 PR 文件，不代表官方已认定**）
> contributor: junshi_liu（兰州大学DSLab）· time: 2026-08-05
> 配套: `knowledge/graph/draft/DRAFT-agetty-vhangup.kv`

## 1. 原始失败与最小复现

最小 C 程序 `repro-vhangup.c`：

```c
#include <unistd.h>
#include <stdio.h>

int main(void)
{
    int r = vhangup();
    printf("vhangup=%d\n", r);
    return r;
}
```

编译/链接命令与关键原始输出（工具链 clang 15.0.4 / SDK `ohos-sdk_26.0.0.18` / `aarch64-unknown-linux-ohos`）：

```
$ clang repro-vhangup.c -o repro-vhangup
repro-vhangup.c:7:10: warning: call to undeclared function 'vhangup'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
        int r = vhangup();
                ^
1 warning generated.
ld.lld: error: undefined symbol: vhangup
>>> referenced by repro-vhangup.c
>>>               /storage/Users/currentUser/tmp/repro-vhangup-8ee0da.o:(main)
clang-15: error: linker command failed with exit code 1 (use -v to see invocation)
```

原始日志来源：执行端本地 `$HOME/tmp/probe-agetty/vhangup-original-diagnosis.txt`（未入库，可复现）。

## 2. 根因分层

1. **声明缺失**：`$SYSROOT/usr/include/unistd.h`、`sys/vt.h`、`sys/*.h` 均无 vhangup 声明 → 编译期 implicit-function-declaration 警告。
2. **libc 符号缺失**：`nm -D $SYSROOT/usr/lib/aarch64-linux-ohos/libc.so | grep vhangup` 无输出（0 导出）→ 链接期 `ld.lld: error: undefined symbol: vhangup`。
3. **内核 syscall 存在**：`$SYSROOT/usr/include/aarch64-linux-ohos/bits/syscall.h` 定义 `__NR_vhangup 58` / `SYS_vhangup 58` → 内核能力存在但 libc 未封装，可 `syscall(SYS_vhangup)` 直调。

（已知矛盾：`knowledge/musl-glibc-full-comparison-iso-posix.md` 记录 vhangup 三 libc 均可用，与 OHOS 26.0.0.18 实测不一致，以实测为准。）

## 3. 适用范围

适用于在同一 SDK（`ohos-sdk_26.0.0.18` / clang 15.0.4 / `aarch64-unknown-linux-ohos`）上调用 vhangup、或类似"libc 未导出但内核 syscall 存在"接口的库/工具（tty 挂断类、登录管理类，如 agetty/sulogin/runuser 等）。不适用于仅因头文件宏配置（如缺 `_GNU_SOURCE`）导致的普通声明遗漏。

## 4. 诊断流程

1. 最小复现：编译调用 vhangup() 的最小程序，观察声明警告与链接失败；
2. 核验 syscall 编号：`grep SYS_vhangup $SYSROOT/usr/include/aarch64-linux-ohos/bits/syscall.h`；
3. 核验 libc 导出：`nm -D $SYSROOT/usr/lib/aarch64-linux-ohos/libc.so | grep vhangup`；
4. 仅当"无声明 + 无导出 + 内核 syscall 存在"时，才在 OHOS 条件启用 syscall shim。

## 5. 修复方案

```c
int vhangup(void)
{
    return (int)syscall(SYS_vhangup);
}
```

- 实现位置：`archives/a/agetty/2.42.2/src/ohos-utmpx-shim.c`（连同 utmpx no-op 降级一起；utmpx 部分归 E121 已覆盖，非本 draft 新贡献）；
- 仅 OHOS 条件（conanfile.py 中 `settings.os == "OHOS"`）启用；
- 非 OHOS 平台不启用 shim，保持上游语义；不伪造 libc API 存在。

## 6. 未解决边界与恢复条件

- libc 恢复导出且头文件声明可用时：移除 shim，恢复正式 API；
- syscall 编号不存在 / 调用返回不支持 / 权限不足时：不得伪造 vhangup 成功，应保留失败并按上游/平台能力记录真实 errno/退出码；
- SDK/内核 ABI 变化时：重新探测 syscall 编号与导出状态；
- shim 仅 OHOS 条件启用，非 OHOS 保持上游语义；
- 真实 TTY/init/登录会话下的运行时行为未验证，取决于内核与权限策略。

## 7. 查重与新增价值

| 已有条目 | 关系 | 原因 |
|---|---|---|
| E121（utmpx API 缺失） | 相似但部分覆盖 | 覆盖同库 utmpx 家族符号（setutxent/pututxline/endutxent + OMIT_UTMP），不含 vhangup，且未覆盖"libc 未导出但 syscall 存在"模式 |
| E014（系统调用不可用） | 相似但根因不同 | 针对"内核未实现 POSIX syscall"（syslog/getrandom，-D 宏禁用）；vhangup 是 libc 未封装而内核 syscall 存在，根因与修复均不同 |
| E003/E004/E015/E027/E050/E078/E085/E090/E092/E093（链接失败类） | 无关 | 均针对库缺失/BIND_NOW/libintl/工具链识别等，与 vhangup 无关 |

**新增价值**：跨库可复用的"libc 未导出 + 无声明 + 链接失败 + 内核 syscall 存在 → syscall shim"分层诊断模式，含适用边界与恢复条件。

## 8. 验证

- 上游 agetty 测试：`0/0 (N/A，无 agetty 适用的上游测试)`；367 为 util-linux 全库脚本背景（tests/ts 91 子目录、367 个可执行脚本，无 agetty 目录、0 个与 agetty 相关），**不是** agetty 测试数；
- 消费者补充 smoke：`2/2 PASS`（`agetty --version` 版本字符串断言 + `agetty --help` 退出码断言，conan create test_package 真实执行）；
- shim 后：agetty 构建、链接、`--version`、消费者 smoke 2/2 全部通过。

## 9. 证据链接

- Wiki: <https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/wikis/OHOS-SDK-26.0.0.18-vhangup-未导出：检测与-syscall-shim>
- 归档 notes: `archives/a/agetty/2.42.2/notes.md`（第 5 节 vhangup 无声明/无导出）
- 归档 manifest: `archives/a/agetty/2.42.2/manifest.yaml`（adaptation.vhangup）
- shim 源码: `archives/a/agetty/2.42.2/src/ohos-utmpx-shim.c`、`ohos-utmpx-compat.h`
- 可复现日志: `$HOME/tmp/probe-agetty/vhangup-original-diagnosis.txt`（执行端本地）

## 10. 元数据

- contributor: junshi_liu（兰州大学DSLab）
- time: 2026-08-05
- source_event: agetty 2.42.2 适配第 2-8 轮真实回报（任务服务 analysis_approved 回报）
- pr_ref: PR pending（未伪造；PR 创建后回填真实编号）
- 本材料用于路径 B 证据审计，**不是 PR 文件，不代表官方已认定**。
