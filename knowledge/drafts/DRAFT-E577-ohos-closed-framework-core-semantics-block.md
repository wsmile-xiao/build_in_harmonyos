# DRAFT-E577 — 闭源平台框架承载核心语义（LaunchServices/Apple Events/CoreFoundation）→ 无可移植子集 → 诚实阻塞

- **编号**: E577（草稿，未合入 `knowledge/graph/`，已通过 draft-review + KC1–KC5 + graph validate）
- **贡献者**: LAUNCH（launch 1.2.5 → OpenHarmony PC 移植审计，分支 feat/launch-1.2.5）
- **日期**: 2026-09-15
- **severity**: 3（blocking）
- **category**: platform, portability, limitation, headers
- **判定**: 平台阻塞（platform-blocked），非配方问题

## 现象（Error Surface）

macOS 专属 CLI 工具交叉编译到 OHOS aarch64 时，首个编译错误即为 Darwin 专属头文件缺失：

```text
clang-15: fatal error: 'sys/attr.h' file not found
#include <sys/attr.h>
         ^~~~~~~~~~~~
1 error generated.
```

修复（删除/替换）该头文件后**不会**进入可编译状态——错误依次暴露为 `CoreFoundation/CFString.h`、`CoreServices/LaunchServices.h`、`CarbonCore/MacTypes.h` 等框架头缺失。这是一个信号：**单点修复无法收敛**，工具的核心语义整体依赖闭源框架。

## 识别（Recognition）

具备以下特征时命中本模式：

1. **首错即平台专属头**：`sys/attr.h`、`mach/mach.h`、`CarbonCore/*.h`、`*.framework/Headers` 等。
2. **修一个漏一个**：每修一个缺失头，下一个错误仍是另一个框架头/符号，不收敛。
3. **核心动词全链路依赖闭源框架**：审计源码发现工具的每个功能动词都调用闭源 API（见下表），不存在只依赖 POSIX 的功能子集。
4. **无上游测试**：上游无测试可证明“部分功能正确”。

## 诊断（Diagnosis）

### 根因

工具的核心功能不是建立在 POSIX 可移植层之上，而是**整体构建于闭源平台框架**。以 launch 1.2.5 为例：

| 核心动词 | 承载 API（闭源） | main.m 行号 |
|---|---|---|
| launch（启动 app/文件/URL，等完成） | `LSOpenItemsWithRole` / `LSOpenURLsWithRole` + Apple Events 等待 | 216, 261 |
| list（列出可启动项） | `LSCopyApplicationURLs` / `LSFindApplicationForInfo` | 409, 431 |
| finder（在 Finder 中显示） | Apple Events → Finder | 216, 261 |
| trash/cdev（移到废纸篓/清倒废纸篓） | Apple Events → Finder | 216, 261 |
| 参数解析/字符串/路径 | CoreFoundation CFString/CFURL/CFBundle/CFRunLoop | 全文件 |
| 缓存扫描（缓存大小计算） | `getattrlist`（Darwin）+ CarbonCore | 101 |
| 进程模型 | `ProcessSerialNumber` / `GetProcessForPID` / `SetFrontProcess` | 507, 897 |

框架未提供源码、未提供 OHOS SDK；OHOS sysroot 不含这些框架的头文件与库。**这些调用点没有可替换实现，也不存在“可移植子集”**——删掉任何一个调用点都等价于删除对应功能动词，工具退化为空壳。

### 与最近邻条目的区别（查重结论）

| 条目 | 根因 | 为何不适用 |
|---|---|---|
| DRAFT-m1ddc | Apple 私有 DDC/CI 传输层缺失，但 **CLI 合约可保留**（传输层可拆分替换） | launch 的核心语义**不可拆分**：每个动词本身就是框架调用 |
| E449 | AppKit 依赖但 **GNUstep 提供开源替代** | launch 依赖 LaunchServices/AppleEvents，**无开源替代**（GNUstep 不实现 LaunchServices） |
| E400 | JIT 能力边界（能力缺失但功能可裁剪） | launch 无可裁剪的核心子集 |

### 验证命令

```bash
tar -xzf launch-1.2.5.tar.gz && cd launch-1.2.5
clang -c -target aarch64-linux-ohos main.m -o /dev/null 2>&1 | head -3
# 未移植时首错 fatal error: 'sys/attr.h' file not found
```

sysroot 框架检查（取证时已执行）：

```bash
# 在 OHOS SDK sysroot 根目录下执行；无输出 = sysroot 无这些框架
find <OHOS_SDK_SYSROOT> \( -iname 'CoreFoundation*' -o -iname 'CoreServices*' -o -name 'libobjc*' -o -iname 'Carbon*' \)
```

## 方案（Solution Space）

### 推荐方案（priority 1）：诚实阻塞（honest-block）

承认平台阻塞：核心语义由闭源框架承载，不存在可移植子集。不得通过空 stub、假实现、删除核心功能或跳过验证宣称适配成功；以源码级证据（调用点行号、sysroot 检查、交叉编译首错）登记 blocked，为未来平台能力变化保留重评估入口。

**安全边界**：blocked 判定要求三重证据闭环：
1. 源码级调用点证据（grep 行号）
2. sysroot 无框架证据（find 无输出）
3. 交叉编译首错证据（clang fatal error）

**失败条件**：若审计发现任一核心动词可脱离闭源框架独立实现（存在可移植子集），或存在开源等价实现（如 GNUstep 覆盖），则本条目不适用，应改按常规移植路径（路径 A）执行。

### 回退方案（priority 2）：框架移植后重评

若上游框架（或开源替代）未来提供 OHOS 支持，重跑 verification_cmd 重新评估；在此之前维持 blocked。

### 禁止策略

| # | 禁止模式 | 原因 | 后果 |
|---|---|---|---|
| 1 | `AESendMessage() {}` 空函数体 stub | 编译通过但语义为空 | 假适配，消费者全部失效 |
| 2 | `#ifdef __OHOS__ return 0;` 隐式空实现 | 与空 stub 同罪，更难审计 | 静默空实现混入上游 |
| 3 | `--no-test` / 跳过测试 | 绕过功能验证门禁 | 无法证明真实语义保留 |

## 元数据

- **doc_file**: doc/E577.md
- **source_event**: launch 1.2.5 (nriley/launch) → OHOS aarch64 可移植性审计
- **similar_to**: DRAFT-m1ddc-apple-ddc-transport-boundary, E449, E400
- **metrics**: 1/0/1.0（1 次成功，置信度 1.0，2026-09-15）

## 校验状态

- [x] draft-review
- [x] KC1–KC5
- [x] graph validate
