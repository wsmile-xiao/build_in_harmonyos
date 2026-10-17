# Embedded RingBuf CPP

一个 header-only 的 C++ 模板环形（循环）缓冲队列库，面向嵌入式平台（Arduino 及其他），
全部内存由模板参数在编译期静态分配，不使用堆内存。

## 功能概述

- `RingBufCPP<Type, MaxElements>` 模板类：定容 FIFO 环形缓冲，支持任意类型（含结构体深拷贝）。
- `add(obj, overwrite=false)`：入队；满且不覆盖时返回 false，满且 `overwrite=true` 时挤掉最老元素。
- `pull(dest)`：出队并拷贝到出参；空缓冲返回 false。
- `peek(num)`：返回第 num 个元素的内部指针（可直接改写），越界返回 NULL。
- `isFull()` / `isEmpty()` / `numElements()`：状态查询。
- `RB_ATOMIC_START` / `RB_ATOMIC_END`：临界区抽象（AVR/ESP8266 有真实实现）。

## OHOS 适配要点

- **补丁 0001（bugfix）**：上游 `RingBufCPP.h` 使用 `size_t` 却不含任何定义 `size_t`
  的标准头。在 OHOS（musl + libc++）下，把 `<RingBufCPP.h>` 作为**第一个** include
  直接 `error: unknown type name 'size_t'`；补 `<stddef.h>` 后自包含，README 记载的
  `#include <RingBufCPP.h>` 用法才能按原样工作。
- **原子性**：非 Arduino 分支里 `RB_ATOMIC_START/END` 展开为普通 `{ }`，**没有**中断或
  线程互斥。上游 README 明示其它平台需要自行实现这两个宏；本包不做多线程并发测试
  （写了就是真竞态），消费者测试只断言宏抽象已定义且可嵌套。
- **`#warning`**：非 Arduino 分支恒有两条 `#warning`（ISR 不安全提示），属上游设计提示，
  不是错误；只有 `-Werror` 的下游才需要自行关闭。
- **上游无测试**：全库 8 个文件、无 `tests/`、无 `make check`/`ctest`/`meson test`；
  唯一含 "test" 的示例 `examples_no_arduino/test.cpp` include 了本版本不存在的
  `RingBuf.h`（实测编译 rc=1）。测试面由本仓库 `test_package/` 的 12 个消费者用例
  （249 条断言）承担，计入「鸿蒙特有测试」行。

## 依赖关系

- 编译依赖：无（零依赖 header-only）。
- 运行依赖：无。

## 参考资料

- 上游仓库：https://github.com/wizard97/Embedded_RingBuf_CPP
- 上游 README（API 说明）：https://github.com/wizard97/Embedded_RingBuf_CPP/blob/1.3/README.md
