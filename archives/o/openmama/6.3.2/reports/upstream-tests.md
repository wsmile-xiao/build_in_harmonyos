# 上游测试用例执行报告 — openmama 6.3.2（HarmonyOS PC / aarch64）

本文件记录**上游 GTest 单元测试套件**在 HarmonyOS PC 真机上的接入方式与实测结果，
所有数字都可由下面的命令在设备上复跑（配方 `build()` 内即执行同一命令）。

## 1. 接入方式

- 上游单元测试是 gtest 工程：`common/c_cpp/src/gunittest/c`、`mama/c_cpp/src/gunittest/{c,cpp}`、
  `mamda/c_cpp/src/gunittest`，由 `-DWITH_UNITTEST=ON` 打开。
- GoogleTest 用制品仓已发布组件 **`gtest/1.17.0.1`** 以 `test_requires` 接入
  （仅配方构建期，不进入消费者传播面）。
- 配方侧接线（上游不认识 Conan，因此用它本来就读的变量）：
  - `GTest_ROOT` / `GTest_DIR` → 指向 gtest 包内的官方 `lib/cmake/GTest` 配置；
  - `GTEST_INCLUDE_DIRS` / `GTEST_BOTH_LIBRARIES` → 上游 `gunittest` CMakeLists 链接用的旧式变量；
  - `CMAKE_GTEST_DISCOVER_TESTS_DISCOVERY_MODE=PRE_TEST`（构建期不执行目标二进制，改由 ctest 执行）。
- **套件按上游默认参数运行**：`gtest_discover_tests(... EXTRA_ARGS -m qpid -p qpidmsg -i Q)`，
  即它默认就要求 **qpid 中间件桥 + qpidmsg payload**（`payload/qpidmsg` 是树内唯一 payload 桥，
  不存在"换一个不带 proton 的桥"的替代路线）。因此配方以
  `requires qpid-proton/0.38.0` + `WITH_PROTON=ON` 把这两个组件真实构建出来。
- **ctest 的加载路径**：`mama_loadBridge` / `mama_loadPayloadBridge` / 插件加载都是**按名字 `dlopen`**
  （`libmamaqpidimpl.so`、`libmamaqpidmsgimpl.so`、`libmamaentnoop.so`、`libmamaplugindqstrategy.so`），
  而本配方从不 `install`，CMake 构建树也不在任何默认加载路径上。上游自己的 CI 是 `make install` 后
  `export LD_LIBRARY_PATH=/opt/openmama/lib`；本配方等价地把构建树内**所有**含 `lib*.so` 的目录
  拼进 ctest 的 `LD_LIBRARY_PATH`。
- 源码侧 build-system 补丁（见 `patches/0007`、`0008`、`0009`、`0010`）：单测目录 `include(GoogleTest)`
  且把单测目标抬到 C++17（上游顶层写死 C++11，而 gtest 1.17 要求 C++17，库本体仍按 C++11 编译）；
  `linux/wombat/wUuid.h` 的 `uuid_generate_time_safe` 退回本平台 libuuid 提供的
  `uuid_generate_time`；以及两处**重复 `pthread_join`** 的平台修复（见第 4 节）。

## 2. 复跑命令

```bash
conan create archives/o/openmama/6.3.2 \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64 \
  --build=missing
# build() 会自行：重签 4 个单测可执行文件 → 以补全的 LD_LIBRARY_PATH 跑 ctest → 打印汇总，
# 完整日志落在构建目录 upstream-ctest.log
```

## 3. 实测规模与结果

| 项 | 值 |
|---|---|
| 构建出的上游单测可执行文件 | 4 个：`UnitTestCommonC`、`UnitTestMamaC`、`UnitTestMamaCPP`、`UnitTestMamdaCPP` |
| ctest 注册用例 | 1929 |
| 其中上游标记为 Disabled | 67（`DISABLED_` 用例，ctest 记为 Disabled，不执行） |
| **实际执行** | **1862** |
| **通过** | **1862** |
| 失败 | **0** —— ctest 原始汇总行：`100% tests passed, 0 tests failed out of 1862` |
| ctest 墙钟用时 | 299 s（真机，串行） |

也就是说：**上游套件在 HarmonyOS PC 上以 1862/1862 全绿**，含全部"打开 MAMA"的用例
（中间件订阅/发布/队列/timer/transport、payload 编解码、field cache、MAMDA 订单簿与行情监听器等）。

## 4. 本轮为让套件真正跑起来修掉的三个平台问题

开 `WITH_PROTON` 后套件第一次真正执行到"打开并关闭 MAMA"的完整路径，暴露了三个此前被
"`mama_open()` 因缺 payload 桥提前失败"掩盖的问题（均与 qpid-proton 本身无关）：

| 现象 | 根因 | 处置 |
|---|---|---|
| 加载路径缺 `libmamaentnoop.so` / `libmamaplugindqstrategy.so`；补全后又大面积 SegFault | ctest 的 `LD_LIBRARY_PATH` 只覆盖 `*impl.so`；而 entitlement 桥与插件同样是**按名字 dlopen** | 加载路径放宽为构建树内所有含 `lib*.so` 的目录（配方内实现，非补丁） |
| 每个"打开+关闭 MAMA"的用例在 `mama_close()` 段错误（107 → 696 条） | `baseBridge_close()` 先取 timer 堆线程号、再 `destroyHeap()`（**内部已 join 该线程并 free 堆**）、然后又 `wthread_join(timerThread)` —— **对同一 `pthread_t` join 两次**。glibc 上多半只返回 ESRCH，musl（本平台）在 `pthread_join` 里解引用已释放的线程描述符 | `patches/0009`：删掉 `baseBridge_close()` 里多余的 join |
| ResourcePool / QueueDispatcher 用例段错误（20 条） | `mamaDispatcher_destroy()`（`mama/c_cpp/src/c/queue.c`）先 `wthread_join(impl->mThread)`，随后 `wombatThread_destroy(name)`（`common/c_cpp/src/c/thread.c`）**又 join 同一条线程** | `patches/0010`：`wombatThread_destroy()` 只管具名线程表项清理，不在其中 join（调用方自己 join） |

定位手法（本机 ptrace 被禁、musl 的 `backtrace()` 返回 0 帧）：LD_PRELOAD 型 SIGSEGV 处理器
（`ucontext` 取 pc/sp + `/proc/self/maps` 归属）+ 生命周期插桩（`mama_loadBridge`/`mama_open`/`mama_close`、
`dlopen`/`dlclose`、`pthread_join`）+ 在构建树源码里加临时 TRACE 标记逐段收窄。
注意：`/system/lib/ld-musl-aarch64.so.1` 在本平台**就是 libc**，pc 落在它里面等于落在
`pthread_join`/`free` 等 libc 函数里，不是加载器问题。

## 5. test_package（真实消费者）同步更新

`WITH_PROTON` 打开后包内不再"只有 stub 桥接"，原先"断言裁剪后果"的两条消费者测试随之更新为
**正向断言**（qpid 桥可加载、`mama_open()` 成功、引用计数正确、`mama_close()` 成功）：

| 二进制 | 断言数 | 覆盖内容 |
|---|---|---|
| `test_openmama_c` | 14 | 版本宏/运行时符号一致性、`mama_loadBridge("noop")`、`mama_getVersion`、**`mama_loadBridge("qpid")` 加载 AMQP 桥**、**`mama_open()` 连同 qpidmsg payload 成功**、`mama_openCount` 计数、`mamaStatus_stringForStatus`、`mama_close` 两次引用 |
| `test_openmama_cpp` | 6 | `Mama::loadBridge("noop"/"qpid")`、`Mama::getVersion`、`Mama::setProperty/getProperty`、**`Mama::open()` 成功 + 引用计数**、`Mama::close` |
| `test_openmama_uri` | 11 | 资源池 URI 解析器（替代 `apr_uri_parse` 的本地实现）逐形态断言 |

三条二进制均 `SUCCESS: 0 check(s) failed`。

## 6. 与裁剪态的对比（历史）

`qpid-proton` 尚未适配时，本配方曾以 `WITH_PROTON=OFF` 提交，上游套件实测
`27% tests passed, 1351 tests failed out of 1862`（通过 511），1351 条失败 100% 命中
`mamaqpidimpl` / `mamaqpidmsgimpl` 不可得这一单一根因。依赖项
`qpid-proton 0.38.0` 随后按官方口径自行导入适配并发布（制品仓已有 `qpid-proton/0.38.0`），
本 PR 打开 `WITH_PROTON` 后即达 1862/1862 全绿。
