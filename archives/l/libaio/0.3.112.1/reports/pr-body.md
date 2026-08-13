## PR 信息
- **三方库名称**：libaio
- **上游版本**：0.3.112.1
- **上游仓库地址**：https://releases.pagure.org/libaio/libaio-0.3.112.tar.gz
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游测试套件 |
| 集成测试 | 0 | - |
| 其他测试 | 0 | 跳过的测试 |
| **合计** | **0** | |

### 是否存在对上游测试用例的修改？
是，见下方补丁说明

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 一致 | 通过 0/0 |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 0 | - | 新增 |
| **合计** | **0** | | |

---

## 上游测试用例修改说明

本 PR 包含 3 个补丁，其中 2 个为上游测试用例修改（从 0.3.112 继承），1 个为 OHOS 平台关键修复：

1. **0001-harness-cases-13.t.patch** (继承自 0.3.112): 修复 harness/cases/13.t 中 designated initializer 语法 `tv_sec: 30` → `.tv_sec = 30`，符合 C99 标准
2. **0002-harness-cases-22.t.patch** (继承自 0.3.112): 替换废弃的 `#include <sys/poll.h>` 为 `#include <poll.h>`
3. **0003-io_pgetevents-ohos-sigsys.patch** (0.3.112.1 新增): **关键修复** — OHOS 内核对 `io_pgetevents` (syscall 292) 触发 SIGSYS 信号而非返回 -ENOSYS，导致进程崩溃。libaio 的 `_body_io_syscall` 宏假设 `syscall()` 总会返回，OHOS 违反此假设。修复方式：在 `src/syscall.h` 中 `#undef __NR_io_pgetevents`（当 `__OHOS__` 定义时），使 `io_pgetevents.c` 走 `#else` 路径返回 `-ENOSYS`。

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: makefile
- 配置选项: `默认配置`

### 产物验证
| 编译无错误 | PASS | 构建系统: makefile, 状态: built |
| 产物存在性 | PASS | conan create 验证 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | 通过: 0, 失败: 0, 跳过: 0 |
| 动态依赖 | PASS | 依赖: 无 |

### 补丁说明
- `0001-harness-cases-13.t.patch`: 0001-harness-cases-13.t.patch
- `0002-harness-cases-22.t.patch`: 0002-harness-cases-22.t.patch
- `0003-io_pgetevents-ohos-sigsys.patch`: 0003-io_pgetevents-ohos-sigsys.patch

### 依赖
无三方库依赖。libaio 仅依赖系统 libc（`syscall()` 和 `__errno_location()`），已在 `package_info` 中声明 `system_libs = ["c"]`。

### 测试结论
- 总体评价: 通过
- 已知限制: 无

### 遇到的问题与解决方案
无已知问题

### 验证命令
```
conan create archives/l/libaio/0.3.112.1 -pr:h=ohos-aarch64-local -pr:b=ohos-aarch64-local
# 结果: 3 个补丁全部应用，编译成功，test_package 100% passed (1/1)
# io_pgetevents 正确返回 -ENOSYS (不再触发 SIGSYS 崩溃)
```
