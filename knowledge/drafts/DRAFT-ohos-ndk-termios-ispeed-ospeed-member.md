# DRAFT-ohos-ndk-termios-ispeed-ospeed-member: OHOS NDK struct termios 成员名 __c_ispeed/__c_ospeed 差异与守卫映射修复

> **Contributor**: sea_crab | **Status**: Draft | **Updated**: 2026-08-31
> **Severity**: 2 | **Category**: harmonyos / ndk / termios / serial / abivariant / portability
> **Source**: c-periphery 1.0.0 HarmonyOS PC adaptation

## 错误特征

```text
src/serial.c:193: error: no member named 'c_ispeed' in 'struct termios'
src/serial.c:194: error: no member named 'c_ospeed' in 'struct termios'
（serial.c 全库 10 处 c_ispeed/c_ospeed 成员访问）
```

## 现象

c-periphery 1.0.0 的 serial 模块直接访问 struct termios 的波特率成员
（c_ispeed/c_ospeed）。OHOS NDK（ohos-sdk 26.0.0.18，clang 15）的
bits/termios.h 中 struct termios 将输入/输出波特率成员声明为
`speed_t __c_ispeed;` 与 `speed_t __c_ospeed;`（双下划线前缀），
POSIX 名 `c_ispeed`/`c_ospeed` 不存在 → 编译报
`no member named 'c_ispeed'/'c_ospeed' in struct termios`。

## 与现有知识的关系

- 无现成 E-entry 直接覆盖"OHOS NDK struct termios 成员名差异 + 守卫映射"场景——
  knowledge/graph 与 knowledge/drafts 对 termios/c_ispeed/c_ospeed 全库 0 命中。
- 同族问题：NDK 其他双下划线前缀成员名/结构体布局差异。

## 根因

OHOS NDK 的 struct termios（aarch64/arm/x86_64 三个 bits/termios.h 均为
`speed_t __c_ispeed;` / `speed_t __c_ospeed;`）使用双下划线前缀成员名，与
POSIX/Linux 规范名 `c_ispeed`/`c_ospeed` 不一致——属平台 ABI 命名差异一族，
纯编译期成员名差异（非功能缺失、非链接问题）。

## 解决方法

**首选（R8 合规，round-4 采用）：POSIX 抽象 API，零平台条件编译宏**——不直接命名
struct termios 的波特率成员，同一份代码全平台生效：

- 设置：`cfsetispeed(t, B)` / `cfsetospeed(t, B)`（标准 B* 速率同时写 `c_cflag` 的
  B* 位与 ispeed/ospeed 成员，全平台语义一致）。
- 读取：`cfgetospeed(&t)` 替代直接读 `c_ospeed`/`__c_ospeed`。
- custom speed（如 128000/135000，sysroot 无对应 B 常量）：`cfsetispeed` 对非标准
  速率**实测返回 -1（拒绝，成员不变）**，无任何无平台宏路径可写入 `__c_ispeed`/
  `__c_ospeed` → **显式返回错误降级**（`SERIAL_ERROR_CONFIGURE`，open 失败分支
  `close+fd=-1` 保证 `serial_close` 安全；set 路径端口保持旧波特率不变）。较上游
  「写入成员+BOTHER 后 tcsetattr 结果未检查」更安全。
- 实证：c-periphery 补丁 patches/0001-ohos-termios-speed.patch（5 hunk +24/-18，
  全部在波特率设置/读取路径），10 处成员访问全部经 POSIX API 消除。

**备选（不推荐，违反仓库 R8）：__OHOS__ 守卫 + 别名宏映射**——round-1~3 曾使用：

```c
#if defined(__OHOS__)
#define c_ispeed __c_ispeed
#define c_ospeed __c_ospeed
#endif
```

> ⚠️ 仓库 `.gitcode/review-memory.md` R8（欺骗性行为检测清单）要求源码和 patches/
> 补丁不得引入平台条件编译宏（`#ifdef __OHOS__` 应通过 POSIX 接口适配）。
> 此映射在 round-4 官方 Web Review bot 指出 R8 后已降级为不推荐备选。
> 若被迫使用，前置核验 sysroot 无同名宏（grep 定义 c_ispeed/c_ospeed 期望 0 命中）。

## 验证

- 复现：clang 交叉编译 src/serial.c → no member named 错误（10 处）。
- 修复后：make CC=clang AR=llvm-ar tests -j1 → 5 个上游测试二进制全部编译成功（5/5），
  serial.c 零 warning。
- POSIX 语义实测（OHOS aarch64 设备）：标准 50..4000000 全 30 档
  `cfsetispeed/cfsetospeed + tcsetattr + cfgetospeed` 读回 **30/30 生效**；
  custom 128000/135000 `cfsetispeed` 返回 -1（拒绝）→ 显式报错降级。
- 功能验证：驱动真实补丁库（/dev/ptmx）——serial_open 115200→get 115200、
  set 9600→get 9600、tostring 报 baudrate=9600、open 128000→SERIAL_ERROR_CONFIGURE、
  set 135000→SERIAL_ERROR_CONFIGURE 且旧波特率不变（13/13 断言通过）。
- 补丁零平台宏：grep 多模式（__OHOS__/__HOS__/__musl__/__linux__/__APPLE__/defined(）
  命中 0。双验证：conan patch_ng（apply_conandata_patches 实际调用的 patch() 实现）
  + git apply --check 均通过。

## 适用场景

OHOS 上适配直接访问 struct termios 波特率成员的 C/C++ serial/终端/调制解调器类库
（串口库、telnet/socat/minicom 类、ncurses 类 termios 使用方等）。同一推广面：
**凡是「NDK 成员名/宏与 POSIX 规范不一致」的字段，一律优先改用 POSIX 抽象 API
（cfsetispeed/cfgetospeed/cfsetospeed/cfgetospeed 等）而非平台宏映射**；sysroot
缺失的扩展常量（如 B128000）需探测 cfset* 行为后决定支持或显式报错，
不得用平台条件编译宏绕过。

## 禁止做法

- **不要引入平台条件编译宏（__OHOS__/__musl__/__linux__/__APPLE__）**——违反仓库
  R8（欺骗性行为检测清单）；官方 Web Review bot 会对补丁中的 `#ifdef __OHOS__`
  报 R8 违规（round-4 实测）。
- 不要逐个删除/改名库内成员访问（低效且污染源码）——改用 POSIX 抽象 API。
- 不要假设 cfsetispeed 支持非标准速率（OHOS NDK 实测返回 -1）——先探测，
  不支持则显式报错降级，不得静默写入无效值。
- 不要把「降级为显式错误」写成「跳过/静默成功」——错误码与 errmsg 必须如实可查。
