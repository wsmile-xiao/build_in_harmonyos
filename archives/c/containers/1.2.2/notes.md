# containers 1.2.2 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile，支持 static_clang / dynamic_clang / static_gcc / dynamic_gcc）
- 编译日期: 2026-09-22
- 编译器: clang (/data/service/hnp/bin/clang, clang version 15.0.4)
- 状态: built

## 来源核验
- 上游: https://github.com/bkthomps/Containers（MIT License, Bailey Thompson, 2017-2025）
- 版本: v1.2.2（tag commit 170129984ce670784ba1147a35d585f0cb854248）
- tarball: https://github.com/bkthomps/Containers/archive/refs/tags/v1.2.2.tar.gz
- SHA-256: 2697da2d4399dbeb999f18d78032a319e8dd19fb13f36872d2c39f578a595c70
  （该值对应 conandata.yml 中 URL 的实际字节；api.github.com tarball 端点同内容不同 gzip 编码为 d81ff0aa705981df526b59d1e6338b8009ae9c42196d87ba72fbdf266d2664e1，两者解压文件集完全一致）
- 类型: 纯 C89 静态/动态容器库（非 CLI，不需要 commands.json）

## 编译步骤

本机仅有 clang（无 gcc），上游 Makefile 的测试目标硬编码 gcc，故使用 clang 直接编译：

```bash
# 库编译（可重现）:
clang src/*.c -c -O3 -fpic && ar rcs containers.a *.o && rm *.o
# 或 make static_clang（等价，实测通过，仅存在 clang 的 -Wtautological 警告，非错误）

# 测试编译（OHOS 适配参数，见下方"遇到的问题"）:
clang src/*.c tst/*.c -Wall -Wextra -Wpedantic -Werror \
  -Wno-tautological-constant-out-of-range-compare -fsigned-char \
  -std=c89 -O3 -ldl -o ContainersTest

# 运行:
./ContainersTest        # -> "Tests Passed", exit 0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make test_optimized` 失败：`gcc: inaccessible or not found` | 上游 Makefile 测试目标硬编码 gcc，OHOS PC 平台无 gcc（仅 clang） | 用 clang 直接编译测试套件（同参数、同 -std=c89 -Werror 严格度）；库本身用 `make static_clang` 即可 |
| 2 | clang 编译报 `-Werror,-Wtautological-constant-out-of-range-compare`（set.c 中 `char` 与 `-1` 比较） | 上游代码原以 gcc 构建；OHOS AArch64 上 `char` 默认为**无符号**，clang 在 `-Werror` 下将 `char == -1` 判为恒假并硬失败（行为差异：gcc 不触发此诊断） | 测试编译追加 `-Wno-tautological-constant-out-of-range-compare` 抑制该平台编译器特有时刻诊断 |
| 3 | 运行断言失败：`Assertion failed: right - left == item[0] (tst/test_set.c:44)` | AVL 树把平衡因子存于节点首字节 `char item[0]`（取值 -1/0/1）；OHOS AArch64 `char` 无符号，`-1` 被解释为 255，`right-left==255` 恒假 → 集合树校验崩溃 | 编译加 `-fsigned-char`，强制 `char` 为有符号，恢复上游 ABI 语义（同一 x86 行为）；修复后 16/16 全过 |

> 说明：修复点仅在选择编译器标志，不改动上游源码、不生成补丁。`-fsigned-char` 是 OHOS（AArch64）与上游 x86 环境在默认 `char` 符号性上差异的最小适配，属于 R8 之外的构建参数适配，非平台宏 stub。

## 依赖版本

- 无第三方运行时依赖；仅链接 libc 与 `-ldl`（测试套件经 dlsym(RTLD_NEXT) 做 malloc/calloc/realloc 故障注入桩）。
- 工具链: clang 15.0.4、llvm-ar、make 4.4.1、python 3.12.9、conan 2.29.1。

## 上游测试全量枚举台账（双口径）

**发现方式**：官方 tag 源码 `tst/` 目录共 17 个 C 文件（test.c 驱动 + 16 个 test_<container>.c 用户测试源），`tst/test.h` 声明 16 个独立用户测试函数。框架内部机制（STUB_MALLOC 宏、dlsym 桩、SECTION/辅助宏、样例、基准、fixture）不计入独立用例。

### 源码声明 -> 构建 -> 注册 -> 执行 逐项映射

| # | 源码声明 (tst/test.h) | 构建目标 | 注册/实例化 | 实际执行 |
|---|------------------------|----------|-------------|----------|
| 1 | test_array() (test_array.c) | ContainersTest | main() 调用 | PASS |
| 2 | test_vector() (test_vector.c) | ContainersTest | main() 调用 | PASS |
| 3 | test_deque() (test_deque.c) | ContainersTest | main() 调用 | PASS |
| 4 | test_forward_list() (test_forward_list.c) | ContainersTest | main() 调用 | PASS |
| 5 | test_list() (test_list.c) | ContainersTest | main() 调用 | PASS |
| 6 | test_set() (test_set.c) | ContainersTest | main() 调用 | PASS |
| 7 | test_map() (test_map.c) | ContainersTest | main() 调用 | PASS |
| 8 | test_multiset() (test_multiset.c) | ContainersTest | main() 调用 | PASS |
| 9 | test_multimap() (test_multimap.c) | ContainersTest | main() 调用 | PASS |
| 10 | test_unordered_set() (test_unordered_set.c) | ContainersTest | main() 调用 | PASS |
| 11 | test_unordered_map() (test_unordered_map.c) | ContainersTest | main() 调用 | PASS |
| 12 | test_unordered_multiset() (test_unordered_multiset.c) | ContainersTest | main() 调用 | PASS |
| 13 | test_unordered_multimap() (test_unordered_multimap.c) | ContainersTest | main() 调用 | PASS |
| 14 | test_stack() (test_stack.c) | ContainersTest | main() 调用 | PASS |
| 15 | test_queue() (test_queue.c) | ContainersTest | main() 调用 | PASS |
| 16 | test_priority_queue() (test_priority_queue.c) | ContainersTest | main() 调用 | PASS |

### 双口径统计

- `source_declared_total` = **16**（官方 tag 源码按可复制枚举规则发现的独立用户测试函数总数）
- `configured_executable_total` = 1（单二进制 ContainersTest，注册 16 个用例；全部实例化）
- `executed_passed_total` = **16**
- 失败数 = 0，未运行/未实例化数 = 0
- 全量通过率: **16/16 (100.0%)**；当前配置可执行集合通过率: 16/16 (100.0%)
- 上游另有 Makefile 目标 test_coverage / test_debug_no_malloc_fail / test_optimized_no_malloc_fail，为同一批用例在不同 -O/桩开关/覆盖率插桩下的重编译变体，不新增独立用例数。

## 验证结果

```bash
$ emulated clang build && ./ContainersTest
Tests Passed        # exit 0
```
---

**编译结束**: 2026-09-22 01:03
**最终状态**: built
