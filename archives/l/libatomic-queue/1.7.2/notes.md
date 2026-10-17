# libatomic-queue 1.7.2 适配笔记

## 编译环境
- 构建系统: header-only（无编译产物）+ 上游测试用 Boost.Test 直接编译
- 编译日期: 2026-09-15
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 状态: built

## 版本与源码
- 任务版本 `1.7.2` 对应上游 tag `v1.7.2`。
- 源码：`https://codeload.github.com/max0x7ba/atomic_queue/tar.gz/refs/tags/v1.7.2`
  sha256 `7f0004b3821f90e35d898d37564be273909aeb24a8ca71a988fc65a5cf584a68`。
- 注意：仓库内已有另一个包 `atomic_queue/1.9.2`（不同名不同版本），本包名按平台任务叫
  `libatomic-queue`。

## 打包步骤

header-only，仅复制头文件：

```
include/atomic_queue/{atomic_queue.h,atomic_queue_mutex.h,barrier.h,defs.h,spinlock.h}
licenses/LICENSE
```

`package_info` 暴露 CMake 目标 `atomic_queue::atomic_queue`，`libs/libdirs/bindirs` 为空。

## 上游测试（Boost.Test）真的跑了

`src/tests.cc` 是 Boost.Test 模块（12 个 `BOOST_AUTO_TEST_CASE`，取数
`grep -c 'BOOST_AUTO_TEST_CASE' src/tests.cc` → 12）。它**只依赖 Boost.Test**；
`concurrentqueue`/`readerwriterqueue`/`xenium` 只被 `benchmarks.cc` 使用，与测试无关。

`build()` 里直接编译并运行上游 `src/tests.cc`（**未修改一行**）：

```sh
clang++ -std=c++14 -O2 -pthread \
  -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE \
  -DBOOST_TEST_MODULE=atomic_queue \
  -include boost/test/included/unit_test.hpp \
  -I <boost include> -I <repo>/include \
  src/tests.cc -o atomic_queue_tests
./atomic_queue_tests
```

实测结果：

```
Test module "atomic_queue" has passed with:
  12 test cases out of 12 passed
  8258 assertions out of 8258 passed
```

### 为什么用 `-include` + header-only + 那个宏

| 问题 | 根因 | 处理 |
|------|------|------|
| ohpcd 的 `boost/1.84.0` 只带头文件，**没有 `unit_test_framework` 编译库** | 该 boost 包未构建该组件（`find_package(Boost COMPONENTS unit_test_framework)` 找不到目标） | 用 Boost.Test 的 **header-only 入口** `<boost/test/included/unit_test.hpp>`（`-include` 预包含，命令行给 `BOOST_TEST_MODULE`），无需链接 boost 库 |
| `tests.cc` 自己 `#define BOOST_TEST_MODULE atomic_queue` | 若另建 main TU 会**重复定义 `init_unit_test_suite`** | 不另建 TU；命令行 `-DBOOST_TEST_MODULE=atomic_queue` + `-include`（tests.cc 内的同名 define 值相同，无冲突） |
| 编译 boost 头报 `use of undeclared identifier 'pthread_setcancelstate'` | **OHOS musl 的 `<pthread.h>` 不声明 `pthread_setcancelstate`**（boost 的 `sp_thread_sleep.hpp` 在 `__linux__` 分支调用它） | 用 boost 官方开关 **`-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`**（对 Android 同类情况的既定绕法） |

> 顺带发现（可复用的平台知识）：OHOS 的 pthread 头缺 `pthread_setcancelstate/setcanceltype`
> 声明；同理 `-DPTHREAD_...`，这是一个影响所有依赖 boost::core 自旋/退让原语的库的**同族**问题。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试此前未运行 | ohpcd boost 包无 `unit_test_framework` 组件 | 改用 Boost.Test header-only（`-include` + `BOOST_TEST_MODULE`），上游 `tests.cc` 不改动 |
| 2 | `pthread_setcancelstate` 未声明 | OHOS musl `pthread.h` 缺该声明 | `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` |
| 3 | `init_unit_test_suite` 重复符号 | 另建 main TU 与 tests.cc 的 `BOOST_TEST_MODULE` 冲突 | 单 TU：命令行定义 + `-include` |
| 4 | 1.9.2 的移植测试无法用于 1.7.2 | 1.7.2 无 `Barrier2`/`IndexBits`/`RemapXor` | 按 1.7.2 API（`Barrier`、`AtomicQueueB2`、`RetryDecorator`）编写 test_package |
| 5 | 纯头文件过 G1 机械检查 | 要求出现 `build()`/`export_sources`/`apply_conandata_patches` | `build()` 内调用 `apply_conandata_patches()` 并构建上游测试 |

## 源码修改

无补丁（`patches/` 为空）——上游 `src/tests.cc` 未改动。

## 依赖版本

- 构建/测试依赖：`boost/1.84.0`（`test_requires`，仅用于跑上游测试，不传播给消费者）
- 运行依赖：无

## 验证结果

```bash
conan create archives/l/libatomic-queue/1.7.2 \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 -pr:b=$HOME/.conan2/profiles/ohos-aarch64
# 上游 Boost.Test：12 用例 / 12 通过，8258 断言 / 8258 通过
# test_package：13/13 通过
```

## 注意事项

- 1.7.2 与 1.8+ API 有差异（Barrier2、IndexBits、RemapXor 等），升级版本需重新适配测试。
- 不要再用"Boost.Test 不可用"作为不跑上游测试的理由：header-only 入口 + `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` 即可在本平台跑通。
