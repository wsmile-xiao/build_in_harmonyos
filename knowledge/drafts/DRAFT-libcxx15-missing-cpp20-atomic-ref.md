# DRAFT-libcxx15-missing-cpp20-atomic-ref

- **id**: DRAFT-libcxx15-missing-cpp20-atomic-ref
- **阶段**: compilation
- **严重度**: 3 (blocking)
- **分类**: libcxx, toolchain, compat, cxx20, portability, libc, concurrency
- **来源事件**: archives/s/smashtable/0.3.1 (patch 0001), 2026-09-05
- **作者**: 73AA

## 错误特征

```
error: no template named 'atomic_ref' in namespace 'std'
error: no member named 'store' in 'ashvardanian::smashtable::atomic_ref<long>'
```

（第二条出现在只补了部分方法的半成品 fallback 上——完整调用面见下。）

## 根因

OHOS SDK26（ohos-sdk_26.0.0.18）配套 libc++ 15.0.4 未实现 C++20 P0019R4
`std::atomic_ref`——上游 libc++ **16.0** 才落地。`<atomic>` 头存在但不含该模板：

- `std::atomic_ref<T>` 模板不存在，任何 `atomic_ref<T> ref{v}` 直接编译失败；
- 无锁/并发库（哈希表 slot 协议、epoch 计数、自旋锁、无锁索引）全部命中；
- 桌面端 libc++ 16+ / libstdc++ 11+ 均已实现，CI 与 OHOS 行为分叉；
- `__has_include(<atomic>)` 探测无效（头存在、内容缺失）。

## 修复方案（推荐，已验证，全工具链可编译）

1. 标准特性宏守卫（R8 能力探测例外，无平台宏）：
   `#if defined(__cpp_lib_atomic_ref) && __cpp_lib_atomic_ref >= 201711L`
   → 用 `std::atomic_ref`。
2. `#else` 提供最小 fallback 类，整型标量调用面逐项映射 `__atomic_*` 内建：

   | atomic_ref 方法 | __atomic 内建 |
   |---|---|
   | `load(order)` | `__atomic_load_n(&ref, (int)order)` |
   | `store(v, order)` | `__atomic_store_n(&ref, v, (int)order)` |
   | `fetch_add/sub(v, order)` | `__atomic_fetch_add/sub` |
   | `fetch_or/xor(v, order)` | `__atomic_fetch_or/xor` |
   | `required_alignment` | `alignof(T)` |

   `std::memory_order` 枚举值与 `__ATOMIC_*` 一致，`static_cast<int>` 直传——
   这正是 `std::atomic` 自身的实现路径，语义等价。
3. `wait(observed, order)` 若被用到：降级 `while (load(order)==expected)
   std::this_thread::yield();` 轮询（无 futex 睡眠语义，仅就绪等待可接受），
   `notify_all()` 空实现——**适用边界写进补丁注释**。

完整 libc++（16+）与 libstdc++ 环境走原路径，行为零变化。

## 验证

- 复现：`clang++ -std=c++20 -c probe.cpp`（`std::atomic_ref<int>` + `fetch_add`）→ 失败
- 修复后：smashtable 0.3.1 `conan create`（ohos-aarch64 profile）→ exit 0；
  上游 9/9 CTest 套件、548 运行时用例真机全过（含 partitioned/locked 并发套件，
  真实驱动 fallback 的 atomic 词汇）；test_package 32 项消费侧 CHECK 全过
- 日志：W3 本地 CI 模拟 `reports/w3-local-ci.log`（真机 ctest 汇总行 `100% tests passed, 0 tests failed out of 9`、9 套件运行时用例 548 全 ok、L1c 消费者测试 ok；reports/ 不入库，证据行已摘录于 test-report.md 与 PR 正文）

## 适用范围

- OHOS SDK26 clang15/libc++15 上所有使用 `std::atomic_ref` 的 C++20 项目
- 间接命中：上游按 P0019 写的并发容器/无锁索引库（移植时整类报错）
- 浮点/指针 `atomic_ref` 同思路可扩展（本实例未用到，未验证）

## 查重

- graph/index.tsv：无 atomic_ref/__cpp_lib_atomic_ref 条目（E 系列 libc 类条目
  E020/E026/E029/E032/E033/E039/E062 均为 musl/glibc 头与运行时问题，不同层面）
- knowledge/drafts/：唯一 atomic 命中 DRAFT-oatpp-1.3.1-ohos-libatomic-version-subdir
  是 `-latomic` 链接与安装布局问题，非头文件能力缺失；format stub / spaceship /
  ranges 三条 libc++15 草稿是同一 SDK 家族的不同缺口（已列入 similar_to）

## 反例与解除条件

- 反例：需要非整型（聚合体）atomic_ref、需要真正 futex 睡眠语义的 wait/notify
  ——本 fallback 不覆盖，需等 libc++16+
- 解除条件：OHOS SDK 升级到 libc++ ≥ 16（`__cpp_lib_atomic_ref` 有定义），
  补丁的 fallback 分支自动失效、原路径生效，无需改回
