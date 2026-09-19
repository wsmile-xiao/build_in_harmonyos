# list — HarmonyOS 适配

## 简介

[clibs/list](https://github.com/clibs/list) 是一个极简的双向链表 C 库（MIT License），
由 TJ Holowaychuk 编写，为 C 程序提供链表节点、双向链表、迭代器与 O(1) 的
push/pop/find/remove 操作。无外部依赖，纯 C99，单头文件 + 3 个源文件的经典
clibs 风格库。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.4.1 | published | 首个 HarmonyOS (aarch64) 适配版本，含消费者验证 + 鸿蒙专项测试 |

## 构建

```bash
# 源码
https://github.com/clibs/list/archive/refs/tags/0.4.1.tar.gz
# SHA-256
1ed72cc11d086e3e40cd6112867cc4102cddf5f008213da5de6e2db587b74340

# 本地编译（纯 Makefile）
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib
make test   # 12/12 上游测试
```

## 使用

```c
#include <clibs/list.h>

list_t *list = list_new();
list_rpush(list, list_node_new("hello"));
list_node_t *hit = list_find(list, "hello");
list_destroy(list);
```

- 安装头文件：`include/clibs/list.h`
- 链接库：`-lclibs_list`（静态 `libclibs_list.a`）
- 包引用：`list/0.4.1`（conan，`ohpcd/stable`）

## 测试

- 上游：12/12 通过（test.c，assert 断言）
- 鸿蒙专项：3/3 通过（大容量压力、分配器钩子、负索引/迭代器）
- 消费者：通过（公开头文件 + 公开 API 完整链路）

详见 `0.4.1/reports/test-report.md`。