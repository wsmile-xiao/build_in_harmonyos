# E6511 — LP64（aarch64）下用 `unsigned long` 承载 32 位网络协议字段：协议帧畸形且无编译告警

- **状态**: 草稿（contributor 6CBB）
- **严重度**: 3
- **触发工具**: test / runtime
- **阶段**: testing / runtime
- **来源事件**: sredird/2.2.2 aarch64-linux-ohos 交叉编译；消费者用例发 RFC 2217 `SET-BAUDRATE 115200`，应答帧不合规

## 症状

- 编译、链接全部成功，`-Wall -W -Wshadow -Wpointer-arith -Wwrite-strings -pedantic` 也没有相关告警；
- 客户端发 `IAC SB 44 1 00 01 C2 00 IAC SE`（设 115200 波特），期望应答
  `IAC SB 44 101 00 01 C2 00 IAC SE`（10 字节），实际收到
  `FF FA 2C 65 00 01 C2 00 00 00 00 00 FF F0`（14 字节，值后多了 4 个 `00`），
  按规定长度读取的客户端读到 `00 00` 而不是 `IAC SE`，后续解析全部错位；
- x86_64 上同样复现（同为 LP64），不是 aarch64 专属，只是在 OHOS 目标上被发现。

## 根因

`sredird.c` 把 32 位的波特率线缆字段声明成 `unsigned long`：

```c
void SendBaudRate(BufferType *B, unsigned long int BR) {
    unsigned long int NBR = htonl(BR);            /* ILP32: 4 字节 */
    ...
    for (i = 0; i < (int) sizeof(NBR); i++)       /* LP64: 循环 8 次 */
        EscWriteChar(B, p[i]);
    ...
}
BaudRate = ntohl(*((unsigned long int *) &Command[4]));   /* 多读 4 字节 */
```

ILP32 时代 `unsigned long` 恰为 4 字节，序列化循环与直接取址读取都碰巧正确。LP64 上
`sizeof(unsigned long) == 8`：发送侧多发 4 个 `00`（小端机上高 4 字节为 0），读取侧多读 4 字节
（`ntohl` 形参是 `uint32_t`，小端机低 32 位恰为前 4 字节，所以读取侧“碰巧对”）。

## 推荐方案（rec_approach: fixed-width-wire-types）

线缆字段改用定宽类型（可移植补丁，无平台宏，可上游化）：

```diff
+#include <stdint.h>
-		unsigned long int NBR;
+		uint32_t NBR;
-		BaudRate = ntohl(*((unsigned long int *) &Command[4]));
+		BaudRate = ntohl(*((uint32_t *) &Command[4]));
```

用消费者用例在 aarch64 上驱动真实协议往返（`test_package/rfc2217_client.c` 的 T5：应答帧逐字节比对，
再回读 pty 从端的 `cfgetospeed()`），补丁前 T5 失败，补丁后 7 项检查全部通过
（qemu-aarch64 实跑，静态重链副本）。

## 兜底方案（fallback_approach: explicit-byte-serialization）

手写 `v>>24, v>>16, v>>8, v` 的逐字节序列化与解析，与类型宽度无关；改动比换类型大。

## 禁止做法

- 用 `__OHOS__` / `__aarch64__` / `__LP64__` 把原类型包一层，或 `-m32`：OHOS 没有 32 位 sysroot，
  且其他 LP64 平台（x86_64 Linux、Alpine）同样复发，补丁无法上游化；
- 只靠“能编译、能启动”判定适配完成：该缺陷在启动与自检阶段完全不可见，只有真实协议往返才暴露。

## 验证

```bash
grep -nE "unsigned long[^;]*\b(NBR|BR)\b|ntohl\s*\(\s*\*\s*\(\(?unsigned long" sredird.c   # 期望：补丁后无输出
qemu-aarch64 ./rfc2217_client ./sredird     # 期望：ALL PASSED (7 checks)，T5 通过
```

## 关联条目

- 相近（LP64/ILP32 类型宽度假设，场景不同）：草稿 `DRAFT-libuninum-2.7-lp64-ilp32-type-assumption-defects`
  （wchar_t 与 unsigned long 传缓冲）——本条聚焦「按 sizeof 展开的线缆序列化 / 直接取址读取」；
- 相近（musl 无 `<termio.h>`）：草稿 `DRAFT-E567-termio-ioctl-macro-capability-guard`（同一适配里的另一处缺失头文件，
  按该草稿处置，未另立条目）。
