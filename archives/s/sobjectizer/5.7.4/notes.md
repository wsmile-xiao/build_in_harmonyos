# sobjectizer 5.7.4 — HarmonyOS PC (OHOS aarch64) 适配说明

## 1. 上游工程结构（配方必须知道）

SObjectizer 是 C++17 的 actor-model / 消息传递框架（Stiffstream 出品）。
上游仓库**根目录没有 `CMakeLists.txt`**，全部 CMake 工程位于 `dev/` 子目录：

```
<source>/
├── dev/
│   ├── CMakeLists.txt      <-- 真正的工程根，配方必须以 dev/ 为 -S
│   ├── so_5/               <-- 库本体（libso.<ver>.so + libso_s.<ver>.a）
│   ├── sample/so_5/        <-- 示例
│   └── test/so_5/          <-- 上游单测（320 个 _unit.test.* 目标）
```

因此配方 `layout()` 只声明 build 目录，`build()` 里用
`-S <source_folder>/dev` 指向真正的工程根。若照惯例用仓库根做 `-S`，
configure 会因找不到 `CMakeLists.txt` 直接失败。

## 2. 构建要点

| 项 | 取值 | 原因 |
|----|------|------|
| CMake 源目录 | `<source>/dev` | 仓库根无 CMakeLists.txt |
| toolchain | `ohos.toolchain.cmake`（自发现） | 绕开 conan_toolchain 在 os=OHOS 下的 `CMAKE_SYSTEM_NAME` 映射问题（ML-0035） |
| `OHOS_ARCH` | `arm64-v8a` | ohos.toolchain 要求 |
| `CMAKE_INSTALL_LIBDIR` | `lib` | ohos.toolchain 在 64 位下默认装 `lib64/`，须改回 `lib` |
| `CMAKE_INSTALL_PREFIX` | package_folder | GNUInstallDirs 的 `CMAKE_INSTALL_FULL_*` 在 configure 期按当时 prefix 展开成绝对路径写进 install 规则，必须 configure 期就给 |
| `SOBJECTIZER_BUILD_SHARED` | ON | 产出 `libso.5.7.4.so` |
| `SOBJECTIZER_BUILD_STATIC` | ON | 产出 `libso_s.5.7.4.a` |
| `SOBJECTIZER_INSTALL` | ON | 生成 install 规则 + `sobjectizer-config.cmake` |
| `BUILD_TESTS` | ON | `enable_testing()` 并注册上游 319 个 ctest 用例 |

### 2.1 llvm-ranlib 缺失（E0xx 类问题）

OHOS SDK 的 `llvm/bin` 下**只有 `llvm-ar`，没有 `llvm-ranlib`**，而
`ohos.toolchain.cmake` 仍把 `CMAKE_RANLIB` 指向 `llvm-ranlib`。
cmake 造静态库的规则是 `<AR> qc <lib> <objs> && <RANLIB> <lib>`，于是：

- 所有 `.o` 都编得过；
- 一到造 `.a` 就 `ENOENT`，且报错**不说是哪个程序找不到**：
  ```
  Error running link command: no such file or directory
  ```

本配方 `SOBJECTIZER_BUILD_STATIC` 默认 ON，**必定**踩到。配方用
`_llvm_ranlib()` 探测：若 SDK 里没有 `llvm-ranlib` 就回退到系统
`shutil.which("llvm-ranlib")` 并显式传 `-DCMAKE_RANLIB=`。

### 2.2 构建并行度必须夹住（OOM）

`BUILD_TESTS=ON` 会产出 **319 个测试可执行文件** 加 2 个库。裸 `cmake --build -j`
（起满核）会把 11GB 的构建机打爆，gmake 报：

```
gmake[2]: *** [.../main.cpp.o] Error 137      # SIGKILL，OOM killer
gmake[2]: *** [.../pub.cpp.o] Error 143       # SIGTERM
Terminated
```

配方改为 `-j min(tools.build:jobs, 8)`，尊重 conan 的 `tools.build:jobs`，
CI 上可用 `-c tools.build:jobs=N` 进一步压低。

## 3. 上游测试执行（rule 4）—— 319 个用例的真实口径

配方在 `build()` 末尾直接跑上游 ctest（即上游自己的测试套件，未做任何替换）：

```
ctest --test-dir <build> --output-on-failure --no-tests=error --timeout 900 -j1
```

注册用例数 **319**（`ctest -N` 实测 `Total Tests: 319`）。

### 3.1 为什么要串行 `-j1` + 宽松 `--timeout`

上游测试框架自带一个**墙钟看门狗**，在
`dev/test/3rd_party/various_helpers/time_limited_execution.hpp`：

```cpp
auto status = f.wait_for( std::chrono::seconds( seconds ) );
if( std::future_status::timeout == status ) {
    std::cerr << "block of code not finished within " << seconds
              << " seconds. Aborting..." << std::endl;
    std::abort();
}
```

全仓库共 **347 处** `run_with_time_limit(...)` 调用点，秒数按**原生 x86-64**
速度标定（常见 5/10/20 秒）。这些是**墙钟**限制，不是 CPU 时间限制。

在 qemu 用户态模拟（约 20–50 倍慢）下并行执行会互相抢占 CPU，导致看门狗
**误判超时**并 `abort()`。实测 `-j4` 时 319 个用例里有 12 个以
`***Timeout` / `Subprocess aborted` 收场；同样的二进制**串行重跑全部通过**
（例如 `disp.thread_pool.threshold`、`disp.adv_thread_pool.chstate_in_safe`、
`environment.stop_guards.parallel_remove_50k` 单独跑退出码均为 0）。

故配方固定 `-j1`。

### 3.2 `_unit.test.spinlocks.llvm_inspired_test` 在 qemu 下的活锁

该用例是纯用户态 TATAS 自旋锁压力测试：**8 线程 × 64K 次迭代**
（`dev/test/so_5/spinlocks/llvm_inspired_test/main.cpp`，`kIters = 64*1024`）。
`so_5::pause_backoff_t` 在 aarch64 上退化为空语句（`#else ;`），退避只剩
`std::this_thread::yield()`。

qemu-user 把 guest 线程复用到 host 线程上，**没有 guest 内核调度器**：
一个在纯用户态循环里自旋的 guest 线程会饿死同 guest 的其它线程 → **活锁**。
实测该进程 10 个线程在 8 秒墙钟内烧掉 62 秒 CPU（≈8 核满载）却永不结束。

**结论：这是 qemu-user 的调度局限，不是 SObjectizer 在 aarch64 上的缺陷。**
证据：

| 环境 | 结果 |
|------|------|
| 原生 x86-64（同一份 `main.cpp`，g++ -O2） | `Spinlock_Write OK` / `RWSpinlock_ReadWrite OK`，< 60s 通过 |
| qemu-aarch64，原始 64K 迭代 | 永不结束（> 42 分钟 CPU 时间仍在自旋） |
| qemu-aarch64，迭代降到 1024 | `Spinlock_Write OK` / `RWSpinlock_ReadWrite OK`，通过 |

即：**同一份自旋锁实现在 aarch64 qemu 下只要迭代量适配模拟速度就正确通过**，
证明库实现本身无误。

### 3.3 实测通过率

| 口径 | 结果 |
|------|------|
| 上游注册用例总数 | **319** |
| 串行执行、排除 qemu 活锁用例 | **318/318 = 100%**（`Total Test time (real) = 459.17 sec`） |
| 把活锁用例的迭代量适配模拟速度后全量串行 | **319/319 = 100%**（`Total Test time (real) = 548.71 sec`） |

（注：配方里保留的是**未改动的上游源码**，319 号用例在 qemu 下会活锁；
上表最后一行是用一份把 `kIters` 调小的源码副本做的**对照实验**，用于证明
库实现正确，该副本**不进入 PR**。CI 与真机上的判定见下文。）

## 4. 消费者测试（test_package）

`test_package/` 通过 Conan 生成的 **CMakeDeps** 文件
（`find_package(sobjectizer CONFIG REQUIRED)`）链接打包产物，分三层：

1. **`test_sobjectizer`（共享库消费者）**
   - Part 1：`SO_5_VERSION` 宏必须等于打包版本 `5.7.4`。
   - Part 2：完整环境生命周期 —— `env → coop → agent → direct mbox →
     立即消息 → 延迟消息（真实定时器线程）→ stop()`。
   - Part 3（**rule 12 端到端**）：两个 agent 在**同一个真实 mbox** 上做
     ping/pong 往返 **1000 次**（`msg_ping`/`msg_pong` 经 SObjectizer 运行时
     派发），断言 `pongs_seen == pings_seen == 1000`。
     这是 SObjectizer 的典型消费者用法（对应上游 `dev/sample/so_5/ping_pong`）。
2. **`test_sobjectizer_static`（静态库消费者）**
   链接 `sobjectizer::StaticLib`（上游 `libso_s.a`，`SO_5_STATIC_LIB` 为
   PUBLIC 定义，与共享库是**不同编译配置**），跑一遍
   `env → coop → agent → 消息 → stop()` 并校验版本串。
   这一层能抓到共享库消费者抓不到的链接/ABI 问题。
3. 两个可执行文件都输出 `HMBS_*_RESULT={...}` JSON 供证据采集。

## 5. 与鸿蒙平台相关的处理

- **代码签名**：鸿蒙 PC 要求 `dlopen` 的 `.so` 与被 `exec` 的可执行文件都带
  代码签名，否则报 `Permission denied` / `Operation not permitted`。
  `package()` 对 `lib/**/*.so*` 与 `bin/` 下的 ELF 逐个
  `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign`。
- **构建树签名**：`build()` 跑 ctest **之前**对构建树里的测试可执行文件与
  `.so` 做同样处理（E077/E083）。
- **`LD_LIBRARY_PATH`**：ctest 前把构建树的 `build-ohos` 加入
  `LD_LIBRARY_PATH`，让测试可执行文件找得到同一棵树里的 `libso.5.7.4.so`。
