# boost1.84-stacktrace_noop 1.84.0 适配笔记

## 任务与形态

- 分支：`feat/boost1.84-stacktrace_noop-1.84.0`
- 包引用：`boost1.84-stacktrace_noop/1.84.0`
- 交付：完整 `boost/` 头文件树和 `libboost_stacktrace_noop.a`
- 类型：独立静态拆分包，不依赖 `boost/1.84.0` 元包
- 状态：DevEco SDK 交叉 `conan create` 及 HDC 运行已验证；仓库 arm64
  本地 CI 因当前环境缺少 profile 指定工具链而阻塞

上游 `libs/stacktrace/build/Jamfile.v2` 对 noop 库只登记
`libs/stacktrace/src/noop.cpp`，`NOOP_DEPS` 为空。选择独立包可以避免与
`boost/1.84.0` 元包的 `Boost` CMake 包名冲突，也不会引入元包未交付的
Stacktrace 组件。

## 源码身份

- 官方 URL：`https://archives.boost.io/release/1.84.0/source/boost_1_84_0.tar.gz`
- SHA256：`a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724`
- 下载大小：145,151,722 bytes
- 完整解压文件数：76,801
- 源码根关键文件：`Jamroot`、`boost/stacktrace.hpp`

## 构建方案

Boost.Build 在当前 HarmonyOS 环境存在 E068 兼容问题。配方从 Conan
`tools.build:compiler_executables` 读取 `clang++`，从同一配置或 PATH
读取 `llvm-ar`，直接编译一个翻译单元：

```text
clang++ -std=c++17 -stdlib=libc++ -O2 -DNDEBUG -fPIC \
  -DBOOST_ALL_NO_LIB -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE \
  -I<boost-root> -c libs/stacktrace/src/noop.cpp -o noop.o
llvm-ar rcs libboost_stacktrace_noop.a noop.o
```

`noop.cpp` 自身定义 `BOOST_STACKTRACE_USE_NOOP`、`BOOST_STACKTRACE_LINK` 和
`BOOST_STACKTRACE_INTERNAL_BUILD_LIBS`，因此库编译命令不重复定义 noop
宏。CMake 消费目标传播 `BOOST_STACKTRACE_LINK`、
`BOOST_STACKTRACE_USE_NOOP`、`BOOST_ALL_NO_LIB` 和
`BOOST_SP_NO_PTHREAD_SETCANCELSTATE`。

## 平台补丁

`0001-boost-core-detail-sp_thread_sleep.hpp.patch` 由
`ohc-run.py refresh-patch --auto` 从官方原始/工作双轨生成，只把三处
pthread 条件增加 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 特性判断。补丁没有
新增 `__OHOS__`，在完整官方源码树执行 `patch --dry-run -p1` 通过。

## 上游测试清点（R51）

- `libs/stacktrace/test/` 有 8 个 `.cpp` 文件。
- `libs/stacktrace/test/Jamfile.v2` 有 74 个静态 `[ run ... ]` 声明；其中
  example 循环会按 6 个 example 文件和各实现后端继续展开。
- 本拆分包执行 Jamfile 中 6 个直接登记的 noop 目标，覆盖 header-only、
  linked library、debug-symbols on/off 三个维度。

| # | 上游目标 | 源文件/形态 | 结果 |
|---|----------|-------------|------|
| 1 | `noop_ho` | `test_noop.cpp + test_impl.cpp`，header-only，debug on | PASS |
| 2 | `trivial_noop_ho` | `test_trivial.cpp`，header-only，debug on | PASS |
| 3 | `noop_lib` | `test_noop.cpp + test_impl.cpp`，链接静态 noop 库 | PASS |
| 4 | `trivial_noop_lib` | `test_trivial.cpp`，链接静态 noop 库 | PASS |
| 5 | `noop_ho_no_dbg` | header-only，debug off | PASS |
| 6 | `noop_lib_no_dbg` | 链接静态 noop 库，debug off | PASS |

未纳入类别及原因：

- backtrace：需要 OHOS 镜像未提供的 libbacktrace，不属于 noop 后端。
- addr2line：运行期依赖外部 addr2line 子进程，不属于 noop 后端。
- windbg/windbg_cached：依赖 Windows DbgEng/ole32，HarmonyOS 不可用。
- basic：由独立 `boost1.84-stacktrace_basic` 拆分包负责。
- example 循环：用于演示断言/异常处理/地址输出等应用级场景；其中
  `terminate_handler` 还引入 Boost.Filesystem 辅助库。它们不增加 noop
  核心库的收集、链接或无调试符号路径，故本最小独立包以 6 个直接登记
  目标作为上游实现合约。
- `stacktrace_torture`：上游标记为 explicit 的长耗时内存压力测试，不是
  默认测试集合，且没有 noop 直接目标。

## 实测环境与结果

本机工具链：DevEco Studio OpenHarmony SDK，OHOS clang 15.0.4，目标
`x86_64-linux-ohos`。运行设备由 HDC `127.0.0.1:5555` 提供，`uname` 为
Linux 5.10.210 x86_64 的 HarmonyOS PC 运行镜像。

### 上游测试

六个程序以 `-static-libstdc++` 交叉链接后发送到
`/data/local/tmp/boost_noop_184`，逐项运行结果：

```text
noop_ho rc=0
trivial_noop_ho rc=0
noop_lib rc=0
trivial_noop_lib rc=0
noop_ho_no_dbg rc=0
noop_lib_no_dbg rc=0
TOTAL 6: 6 passed / 0 failed
```

### 消费者测试

- 通用消费者：空栈、size、迭代器、复制比较、格式化、内存安全 dump。
- HarmonyOS 特有消费者：编译期检查 `__OHOS__` 和
  `BOOST_STACKTRACE_USE_NOOP`；多层 `BOOST_NOINLINE` 捕获仍为空；内存
  dump 只写一个零指针终止项；文件 dump 返回零且无有效帧数据。

HDC 运行结果为通用 1/1、HarmonyOS 特有 1/1，两个进程均 `rc=0`。

### Conan 交叉构建

2026-09-09 使用临时双 profile 执行完整 `conan create`：build profile 为
Windows x86_64，host profile 为 OHOS 6.0 x86_64；host 编译器包装 DevEco
SDK clang 并注入 `--target=x86_64-linux-ohos` 与 sysroot。设置
`BOOST_STACKTRACE_NOOP_HDC` 后，配方通过随包导出的 `hdc_runner.py` 将
每个目标发送到设备，并读取显式的设备端退出码标记，避免把 HDC 本地
进程的成功误判为目标程序成功。

完整流程完成官方源码下载与 SHA256 校验、补丁、静态库构建、上游 6/6、
打包、CMake 消费者构建和设备端消费者 2/2。生成包设置为
`os=OHOS`、`os.version=6.0`、`arch=x86_64`、`compiler=clang 15`、
`libcxx=libc++`，包 ID 为
`7a04d520acd845b96f805ffbcc51fac5b17a209e`。归档库含 `noop.o`，并导出
Boost.Stacktrace noop 的 `collect`、`dump`、`to_string` 等预期符号。

HDC runner 与配方集成的 4 个行为测试同时通过，覆盖正常发送/执行、设备端
非零退出、HDC 返回码为零但输出报告传输失败，以及上游测试链接必须通过
Conan `conanbuild` 环境四种路径。

## CI PR #9040 链接环境修复

CI #42561 中静态库对象编译和归档成功，但六个上游测试均在链接阶段报告
`clang-15: error: linker command failed due to signal`。OHOS profile 将 SDK
`llvm/lib` 通过 Conan buildenv 加入 `LD_LIBRARY_PATH`，该目录提供 lld
运行所需的 `libxml2.so.16`。库编译使用 `self.run()`，会加载 buildenv；
测试链接原先直接调用 `subprocess.Popen()`，绕过了这层环境，导致 lld
启动失败。修复后测试链接统一使用 `self.run(..., ignore_errors=True)`，
既继承 profile buildenv，也保留六项逐项失败统计；测试程序的执行与 HDC
设备端退出码检查保持不变。
