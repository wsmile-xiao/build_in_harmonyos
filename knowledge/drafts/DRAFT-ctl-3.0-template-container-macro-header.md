# DRAFT-ctl-3.0-template-container-macro-header：宏模板容器头的包含模式

## 现象

适配 ctl 3.0（rurban/ctl，纯头文件 C 模板容器库）编写 test_package 时连续报错：

- `ctl/vec.h: error: "Template type T undefined for <vec.h>"`
- `ctl/str.h: error: "Template type T defined for <str.h>"`
- 链接期 `ld.lld: error: undefined symbol: vec_int_size`

## 根因

宏模板容器库用「宏 + include」实例化：`#define P`、`#define T <type>` 后
`#include <vec.h>` 生成 `vec_int` 全套 API。每个模板头**在其末尾自行 `#undef T`**
（vec/lst/deq/set/ust/stk/que/pqu 均如此），于是：

1. 连续 include 多个模板头却只定义一次 T → 第二个头报 "T undefined"；
2. 库内的**非模板头**（str.h 是固定的字符串类型）在 `#ifdef T` 处主动报错
   "T defined"，包含前必须 `#undef T`/`#undef P`；
3. `size`/`capacity` 是结构体字段（`v.size`），并非 `vec_int_size(&v)` 函数——
   按函数调用在链接期才暴露未定义符号。

## 修复模式

- 每个模板头单独定义：`#define P` + `#define T int` + `#include <vec.h>`；
- 包含非模板头前先 `#undef T`、`#undef P` 再 `#include <str.h>`；
- 访问容量/大小用字段（`v.size`、`s.size`），不猜测 `*_size()` 函数；
- 与上游 `tests/func/*` 的用法保持一致（上游 test 文件即按此模式编写）。

## 验证要求

- 消费者/测试源码在 OHOS 工具链（`aarch64-unknown-linux-ohos-clang`）下编译 exit 0；
- 实际运行输出 PASS 且退出码 0；
- 若对某 API 形态不确定，先用最小探针编译运行验证，禁止凭命名猜测。

## 适用边界与反例

- 适用：uthash 类宏模板容器/结构库的 test_package、消费者用例、适配编写；
- 反例：普通非模板 header-only 库（如 dr_wav 单头库）不存在 T 定义问题，
  无需该模式；此处仅针对「宏实例化 + 头内 undef」型库。
