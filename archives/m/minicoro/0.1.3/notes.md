# minicoro 0.1.3 适配笔记

## 编译环境
- 构建系统: 无（header-only 单头文件库；上游仅 tests/Makefile 驱动测试）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（aarch64-linux-ohos，OHOS SDK 26.0.0.18）
- 状态: built（OHOS Conan 消费者测试与上游测试均已通过；尚未进入 release upload）

## 官方来源核验
- 上游 URL: https://github.com/edubart/minicoro（tag v0.1.3，commit 040f337）
- 源码包: https://github.com/edubart/minicoro/archive/refs/tags/v0.1.3.tar.gz
- SHA-256: 4f9d4c3b5f6473f8141ee45e9947a6e7e7ee6665b4d9a8c373c0602495c5f6c9
  （两次独立下载比对一致；init-build 搜索引擎给出的 Savannah/waterlan
  "minicoro" 是同名不同项目，已拒绝，坚持官方 edubart 源）
- 头文件版本标注: `minicoro - v0.1.3 - 27/Jan/2022`

## 适配要点

minicoro 是单头文件协程库，无库二进制，无需 configure/cmake：

```c
#define MINICORO_IMPL   /* 恰好一个翻译单元 */
#include "minicoro.h"
```

- `package_type = "header-library"`，`package_id()` clear → 单一 package_id
- aarch64 自动命中 `MCO_USE_ASM` 汇编实现（minicoro.h ~L1081 `__aarch64__`），
  无平台宏补丁
- 消费者测试真实调用 mco_create/mco_push/mco_pop/mco_resume/mco_yield/
  mco_status/mco_destroy，验证 storage 双向交换与状态机

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 默认下载 github.com 返回 HTML | 执行机对 github.com 直连被网络层改写 | 改用 `api.github.com/.../tarball/v0.1.3` 与 `codeload.github.com/.../v0.1.3.tar.gz` 下载，SHA-256 两次一致后写入 conandata |
| 2 | init-build URL 搜索给出 Savannah/waterlan 同名包 | 搜索引擎把同名不同项目（网络流量计费工具）当作候选 | 按任务「官方来源」强制约束拒绝，坚持 edubart/minicoro 官方源 |
| 3 | `/tmp` 只读且 100% 占满 | 执行机 /tmp 挂载为满的只读块设备 | 全程使用 `$HOME/tmp`（$TMPDIR）作临时目录 |

## 依赖版本

无第三方 Conan 依赖；仅目标平台 C 标准库（mt-example 额外用 pthread，
测试阶段按需链接）。

## 验证结果

```text
OHOS：Conan 2.29.1 / Clang 15.0.4 (aarch64-linux-ohos) / CMake
OHOS conan create：通过；包产物为 include/minicoro.h 与 licenses/LICENSE
OHOS test_package：1/1 可执行消费者通过，12/12 断言通过
OHOS 上游 make test：按 tests/Makefile 目标逐项运行（见上游测试台账）
源码 SHA256：4f9d4c3b5f6473f8141ee45e9947a6e7e7ee6665b4d9a8c373c0602495c5f6c9
```

## 交付物

| 文件 | 说明 |
|------|------|
| `include/minicoro.h` | 单头文件 API 与实现（aarch64 汇编路径） |
| `licenses/LICENSE` | 上游许可证（MIT / Unlicense 双许可） |

配方不包含预编译二进制或库文件。

## 注意事项

这是 header-only 库。使用者必须只在一个 C/C++ 翻译单元定义
`MINICORO_IMPL`。默认栈大小 57344 字节（MCO_DEFAULT_STACK_SIZE），
可通过 mco_desc_init 传入自定义栈大小。
---

**编译结束**: 2026-09-18 11:28
**最终状态**: built
