# openmama 6.3.2 — HarmonyOS PC 适配笔记

## 1. 依赖形态：qpid-proton 已适配发布，本版按上游默认形态构建（不再裁剪）

### 1.1 制品仓实证

```
$ conan list "qpid-proton/0.38.0" -r=ohpcd  → 命中（含 OHOS/armv8/clang15 制品）
$ conan list "*openmama*"        -r=ohpcd  → Found 0 pkg/version recipes   （W0 查重：本库未发布）
$ bash ci/scripts/preflight_check.sh openmama/6.3.2  → 预检通过
```

已发布的可用依赖：`apr/1.7.6(.1)`、`libevent/2.1.13`、`e2fsprogs/1.47.4`（提供 libuuid）、
**`qpid-proton/0.38.0`**（依赖项，PR #11797 已合入并发布，`2026-09-26`）。
**`apr-util` 不存在**（`conan list "apr-util*"` 为 0，`conan download apr-util/1.6.1 -r=ohpcd --only-recipe` 报 `system acceleration policy not enabled`——该文案即"制品仓无此包"，见团队记忆）。
注：仓内 `archives/a/apr-util/1.6.3` 配方已随 main 合入（commit `0eef1b8cff`），但**制品仓没有该版本的制品**，
因此在配方里声明它必然解析失败，只能按 1.3 节的方式处理并如实记录。

**测试框架可用**：`conan list "gtest*" -r=ohpcd` →
`gtest/1.17.0`、`gtest/1.17.0.1`、`gtest/1.17.0.2` 均已发布，另有 `googletest/1.12.1|1.17.0|release-1.12.1`。
上游 gtest 单测接进来后**已 1862/1862 全绿**，见第 4.1 节与 `reports/upstream-tests.md`。

**`qpid-proton` 是 `bridge/qpid` 与 `payload/qpidmsg` 的唯一依赖**，也是上游单测
`-m qpid -p qpidmsg` 的默认前提。本版以 `requires qpid-proton/0.38.0` + `WITH_PROTON=ON`
把这两个组件真实构建出来（并因此让上游套件全绿）。

### 1.2 proton 的开合面（源码级证据链，用于确认改动范围）

1. **唯一 CMake 消费点被开关完整包裹**
   - 顶层 `CMakeLists.txt:125`：`if (WITH_PROTON) find_package(Proton REQUIRED) endif()`
   - `mama/CMakeLists.txt:68`：`if (WITH_PROTON) add_subdirectory(bridge/qpid) add_subdirectory(payload/qpidmsg) endif()`
2. **源码级 grep（`-i proton`，*.c/*.cpp/*.h/*.hpp）只命中 16 个文件**：
   - `mama/c_cpp/src/c/bridge/qpid/*`（8 个）
   - `mama/c_cpp/src/c/payload/qpidmsg/*`（6 个）
   - 唯一例外 `mama/c_cpp/src/c/mama/integration/bridge/base.h` 的两处命中**都在注释里**（"proton middleware message encapsulation"），无代码依赖
   - 即：`WITH_PROTON` 只影响这两个组件，其余组件（libmama / libmamacpp / libmamda / wombat / base 桥 / noop / ompb / 各插件）与之无关
3. **`WITH_PROTON=ON` 后包内可用的中间件与 payload**：base 桥接（真实桥接的参考实现）、
   noop stub 桥接、ompb playback 桥接、**qpid AMQP 桥接（`libmamaqpidimpl.so`）**、
   **qpidmsg payload（`libmamaqpidmsgimpl.so`）**、dqstrategy 插件、noop entitlement，
   以及 libmama（C API + 中间件分发引擎 + 字段/字典框架）、libmamacpp（C++ 绑定）、
   libwombatcommon(+cpp)、libmamda 全系、上游全部示例与测试工具（bin/ 下 40+ 个可执行文件）。

### 1.3 apr-util 缺失的处理（读 CMake 实际要求后定）

- `mama/c_cpp/src/c/CMakeLists.txt:133-134` **无条件**把 `${APRUTIL_LIBRARY}` 加进 libmama 链接行 → 变量必须非空，否则 `-lAPRUTIL_LIBRARY-NOTFOUND` 链接失败
- 全树审计 apr-util 的真实使用：`#include <apu.h>` **零处**、`apu_*` 符号 **零处**；唯一命中是 `apr_uri_parse`
  - `mama/c_cpp/src/c/resourcepool.c`（C）
  - `mama/c_cpp/src/cpp/MamaResourcePool.cpp`（C++）
- 处理：补入等价的本地实现 `mamaResourcePoolUri_parse`（**由 APR pool 持有结果，与 apr_uri_parse 同生命周期**，scheme/authority/path/query 语义对齐，path 保留前导 '/' 以免改变 `originalPathLength` 的既有判定），并把 `APRUTIL_INCLUDE_DIR/APRUTIL_LIBRARY` 指向 apr 包本身以让上游链接行可解析（不引入任何 apr-util 符号）
- **实现要点（AI 检视意见整改后）**：与 `apr_uri_parse` 一样**每个分量各自从 pool 复制一份**（`apr_pstrmemdup`），而不是在 `uri` 缓冲里就地写 `\0` 来切分——就地切分会把 authority 后面的 `/` 或 `?` 覆写成 `\0`，导致 `mPath` 退化为 `""`、`mQuery` 丢失（`mama://transport/source/topic` 的 path 会变成空串）。
  现在的切分顺序是：先按 `#` 定界（fragment 不参与）→ 取出 query（它在 `?` 之后，可能紧跟 authority）→ scheme（小写化）→ authority（到 `/` 或 URI 结束）→ path（其余部分，可能为空串）。
  各形态的实测断言见 `test_package/test_openmama_uri.c`（9 个 URI + 2 个非法入参）。

## 2. 平台适配（10 个补丁，逐条给证据）

| 补丁 | 触发症状 | 实测证据 |
|---|---|---|
| `0001-port-h-posix-portability` | ①`PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP`/`PTHREAD_MUTEX_RECURSIVE_NP` 不存在 ②`INVALID_THREAD (-1)` 编译失败 ③`pthread_setaffinity_np` 未定义引用 | ①`clang -E` 探针：两个宏均 MISSING ②`pthread_t` 即 `struct __pthread *`，`return (-1)` 报 `incompatible integer to pointer conversion`（硬错误）③`nm` OHOS libc：`pthread_setaffinity_np` 缺失，但 `sched_setaffinity` + `pthread_gettid_np` **均在** → 用这两个实现同一语义 |
| `0002`/`0003` resourcepool URI | 链接期 `undefined reference to apr_uri_parse` + 编译期 `'apr_uri.h' file not found` | 见 1.3（含 AI 检视意见整改：分量改为各自 pool 复制，避免就地写 `\0` 丢 path/query；回归测试 `test_package/test_openmama_uri.c`） |
| `0004-noop-bridge-loadable-name` | 随包发布的 stub 桥接无法加载 | 上游 `mama_loadBridge("noop")` 会 dlopen `mamanoopimpl` 并 dlsym `noopBridge_init`，但 CMake 里 `BRIDGE_STUB_NAME=rabbitmq`（产物是 `libmamarabbitmqimpl.so`）→ 文件与符号两边都对不上，改成 `noop` 后加载成功（测试断言 `mama_loadBridge("noop")==OK`） |
| `0005-mamda-examples-optional-curses` | configure 失败：`Could NOT find Curses` | `mamda/c_cpp/src/examples/orderbooks/CMakeLists.txt` 用 `find_package(Curses REQUIRED)`；本平台不引入 ncurses（系统同名库，R26 风险），改为可选依赖：有 curses 才编 bookviewer |
| `0006-perf-tools-x86-only` | 编译失败：`invalid output constraint '=a' in asm`、`use of undeclared identifier 'M_TRIM_THRESHOLD'` | `mamaconsumerc_v2.c`/`mamaproducerc_v2.c`/`mamapingpongc.c` 用 x86 `rdtsc` 内联汇编与 glibc 专有 `M_TRIM_THRESHOLD`/`M_MMAP_MAX`；按 `CMAKE_SYSTEM_PROCESSOR` 收窄为仅 x86 构建 |
| `0007-gunittest-gtest-cmake` | ① configure 失败 `Unknown CMake command "gtest_discover_tests"` ② 编译失败 `C++ versions less than C++17 are not supported`（gtest 1.17 头） | ① 上游 `gunittest` 的 CMakeLists 直接调用 `gtest_discover_tests()`，该命令由 CMake 自带的 GoogleTest 模块提供，而 `find_package(GTest)` 走 config 模式时不会加载它 → 在 4 个单测目录补 `include(GoogleTest)` ② 上游顶层 `CMakeLists.txt:4` 写死 `CMAKE_CXX_STANDARD 11`，而 `gtest/1.17.0.1` 要求 C++17 → 只把这 4 个单测目录的标准抬到 17（库本体仍按上游 C++11 编译，不改全局） |
| `0008-uuid-generate-time-safe` | 编译失败 `use of undeclared identifier 'uuid_generate_time_safe'`（单测 `common/c_cpp/src/gunittest/c/port.cpp:103`） | 本平台 libuuid（e2fsprogs 制品）**只有** `uuid_generate`/`uuid_generate_random`/`uuid_generate_time`（头文件实测），util-linux 才补的 `_time_safe` 变体不在其中；该入口在全树唯一使用点就是这条单测 → `linux/wombat/wUuid.h` 退回到同族 `uuid_generate_time`（产出仍是合法 uuid，仅少"并发下保证不复用"语义） |
| `0009-base-bridge-no-double-join` | 打开 `WITH_PROTON` 后，所有"打开+关闭 MAMA"的上游用例在 `mama_close()` 段错误（`pthread_join` 内） | `baseBridge_close()`：先 `timerHeapGetTid()` 取线程号，再 `destroyHeap()`（**内部已 `wthread_join` 该线程并 `free` 堆**），最后又 `wthread_join(timerThread)` → 对同一 `pthread_t` join 两次。glibc 上多半只返回 ESRCH，musl（本平台）在第一次 join 时已归还线程描述符，第二次 join 解引用已释放内存 → SIGSEGV。删除该次多余 join（`timerHeapGetTid` 也随之无用） |
| `0010-thread-destroy-no-double-join` | ResourcePool / QueueDispatcher 用例段错误（`pthread_join` 内），其余队列相关用例正常 | `mamaDispatcher_destroy()`（`mama/c_cpp/src/c/queue.c`）先 `wthread_join(impl->mThread)`，随后 `wombatThread_destroy(name)`（`common/c_cpp/src/c/thread.c`）**又对同一条线程 join 一次**（该函数本职是"具名线程表"表项清理，调用方 join 才是为了保证线程结束）→ 同 0009 的重复 join。去掉 `wombatThread_destroy()` 中的 join，表项清理语义不变 |

### 2.1 没有打补丁但同样是平台问题（用参数解决）

- **CMake 不识别 HarmonyOS（知识条目 E092）**：`-DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64`
  - 不解决会怎样？① `string(TOLOWER ${CMAKE_SYSTEM_NAME} system)` 拼出 `common/c_cpp/src/c/harmonyos`（不存在）→ `wombat/wConfig.h` 找不到；② `if(UNIX)` 为假 → 上游 `else()` 分支给 libmama 链 **`rpcrt4`**（Windows RPC 库）→ `ld.lld: unable to find library -lrpcrt4`
  - 仓内既有先例 160 处，故沿用而非逐文件打补丁
- **UUID 头文件位置**：上游假设 libuuid 是系统库（`<wombat/wUuid.h>` 直接 `#include <uuid/uuid.h>`），而头在 e2fsprogs 包内 → 用 `clang++ -print-file-name` 无关的普通 `-I` 注入（`tc.extra_cflags/cxxflags`）
- **静态产物 PIC**：`CMAKE_POSITION_INDEPENDENT_CODE=ON`（包内同时发布 .so 与 .a）
- **依赖库路径钉死（构建自洽化）**：上游 `FindAPR`/`FindLibevent`/`FindUUID` 除了 `${APR_ROOT}`/`${LIBEVENT_ROOT}`/`${UUID_DIR}` 之外还会搜默认路径，而 CMake 也会搜由 `PATH` 推出的前缀——CI profile 把 `$HOME/usr/local/bin` 放进了 `PATH`，于是 `$HOME/usr/local/lib` 也在搜索范围内。因此把 `APR_LIBRARY`/`APR_INCLUDE_DIR`/`APRUTIL_LIBRARY`/`APRUTIL_INCLUDE_DIR`/`LIBEVENT_LIBRARIES`/`LIBEVENT_INCLUDE_DIRS`/`UUID_LIBRARY`/`UUID_INCLUDE_DIR` 作为 **cache 变量**交给 CMake（`find_library`/`find_path` 见到 cache 值即跳过搜索），保证链接的永远是本配方声明的 Conan 包。
  动因（实测）：CI worker `CI-021` 上两次构建在 `libmamabaseimpl.so` 处报
  `make[2]: *** No rule to make target '/storage/Users/currentUser/usr/local/lib/libssl.so'`，而同一份代码在 `CI-007`/`CI-020` 全绿——即该文件依赖来自 worker 侧 `$HOME/usr/local` 的残留 OpenSSL，而非本 PR 的代码；钉死后该入口被彻底切断。
- **链接失败自诊断**：`build()` 在 `cmake.build()` 抛错时打印 CMakeCache 里 `APR/LIBEVENT/UUID/SSL/OPENSSL` 的解析结果（见 `_report_link_inputs`），CI 日志末尾即可看到"到底链接到了哪个库"，避免再出现只能从截断日志里猜的情况。
- **Proton 路径同样钉死**：上游 `cmake/FindProton.cmake` 的**库**查找带 `NO_DEFAULT_PATH`，但**头**查找会去 `/usr/local/include`、`/usr/include` 等默认路径；若 worker 上残留一份 proton 头就会"头找到、库找不到"。因此把 `PROTON_ROOT`/`PROTON_INCLUDE_DIR`/`PROTON_LIBRARY` 作为 cache 变量钉到 qpid-proton 包（与 APR/Libevent/UUID 同一处理）。
- **ctest 运行时的加载路径**：`mama_loadBridge`/`mama_loadPayloadBridge`/插件加载都**按名字 dlopen**，本配方从不 `install` 所以构建树不在任何默认加载路径上。上游自己的 CI 是 `make install` 后 `export LD_LIBRARY_PATH=/opt/openmama/lib`；本配方等价地把构建树内**所有**含 `lib*.so` 的目录拼进 ctest 的 `LD_LIBRARY_PATH`（`libmamaqpidimpl.so`/`libmamaqpidmsgimpl.so`/`libmamaentnoop.so`/`libmamaplugindqstrategy.so` 都靠它被找到）。


## 3. 两个"硬骨头"：签名与递归互斥量

### 3.1 OHOS 代码签名：安装阶段改写字节即失效

现象：`conan create` 构建、链接全部成功，测试二进制启动后**所有**包内 .so 都报
`Error loading shared library libmama.so: Permission denied`（引导器连文件都拒绝打开）。

定位过程（逐步收敛）：
1. 同目录下 `libprobe.so`（自己编的）能 dlopen，包内 `libwombatcommon.so` 也能，其它全部失败
2. 用 `llvm-objcopy -p` 对比 **构建树副本 vs 安装副本**：构建树副本 `dlopen OK`，安装副本 `Permission denied`，两者大小相同但内容不同（首个差异字节 155310）
3. `llvm-objdump -p` 显示构建树副本有 `RUNPATH=<...>/build/Release/common/c_cpp/src/c:`，**安装副本的 RUNPATH 被 CMake 抹掉** → 安装阶段原地改写了 ELF
4. 鸿蒙的代码签名是内容哈希（存 `.codesign` 节），链接后再改字节即失效 → 引导器按"签名不匹配"拒绝加载

解法（仓内 248 处同类先例的标准做法）：`package()` 末尾对 `lib/**/*.so` 与 `bin/*` 逐个
`llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1`。
test_package 里自己新链接出来的消费者二进制同样要签（否则 exec 也被拒）。

> 复制文件**不会**破坏签名（哈希随内容一起搬），只有原地改写才会——所以这里只需在打包末尾重签一次。

### 3.2 静态递归互斥量：`mama_open()` 永久挂起

第一次全绿构建后，测试卡在 `mama_open()`：`Attempting to load mama.properties ...` 之后进程不再前进（外层 3000s 超时被杀）。

- 机制：上游把若干静态锁声明为**递归锁**（`PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP`），例如 `common/c_cpp/src/c/properties.l:38` 的 `lexerLock`、`mama.c:234` 的 `myLock`。属性词法锁会被同线程重入，用**非递归**初始化就会自死锁。
- 本平台没有该宏（也没有 `PTHREAD_RECURSIVE_MUTEX_INITIALIZER`），只有 `PTHREAD_MUTEX_RECURSIVE 1`。- 实测确认本平台互斥量结构首字段即类型：`PTHREAD_MUTEX_INITIALIZER` 是 `{{{0}}}`，而
  `static pthread_mutex_t m = {{{PTHREAD_MUTEX_RECURSIVE}}};` 可以同线程连续两次 `pthread_mutex_lock` 成功（探针程序验证）。
- 因此 `WSTATIC_MUTEX_INITIALIZER` 的回退改为 `{{{PTHREAD_MUTEX_RECURSIVE}}}`，一处改动修好全部静态递归锁站点。**修复后挂起消失，测试跑完**。

## 4. 测试

`conan create`（`--build=missing`，profile `ci/conan/profiles/ohos-aarch64`）实测结果：

```
$ conan create . -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
rc=0
  [ok] × 31  →  三条 SUCCESS: 0 check(s) failed
```

test_package 三个真实消费者（都实际调用包内 API，非空壳）：

| 二进制 | 覆盖内容 | 断言数 |
|---|---|---|
| `test_openmama_c` | 版本宏/运行时符号一致性、`mama_loadBridge("noop")` 加载随包 stub 桥接、`mama_getVersion`、**`mama_loadBridge("qpid")` 加载 AMQP 桥**、**`mama_open()` 连同 qpidmsg payload 成功**、`mama_openCount` 引用计数、`mamaStatus_stringForStatus`、`mama_close`（两次引用） | 14 |
| `test_openmama_cpp` | `Mama::loadBridge("noop"/"qpid")`、`Mama::getVersion`、`Mama::setProperty/getProperty`（属性子系统往返，同时覆盖 3.2 的锁修复）、**`Mama::open()` 成功 + 引用计数**、`Mama::close` | 6 |
| `test_openmama_uri` | 资源池 URI 解析器（替代 apr_uri_parse 的本地实现）逐形态断言：标准三段式、query 紧跟 path、query 紧跟 authority（无 path）、空 authority（`///`）、无 authority（`:`）、尾随 `/`、fragment 剔除、scheme 大小写不敏感/其余保留、无 scheme 拒绝、非法入参拒绝 | 11 |

### 4.1 上游测试情况（真机实测，1862/1862 全绿）

上游单元测试是 gtest 工程（`common|c_cpp|mamda` 三处 `gunittest/`），`-DWITH_UNITTEST=ON` 打开，
GoogleTest 走制品仓已发布的 `gtest/1.17.0.1`（`test_requires`），配方 `build()` 内真机执行
`ctest --timeout 60`。套件按上游默认参数注册（`-m qpid -p qpidmsg`），本版以
`requires qpid-proton/0.38.0` + `WITH_PROTON=ON` 把这两个组件真实构建出来。
实测（详见 `reports/upstream-tests.md`，可用同一条 `conan create` 复跑）：

```
ctest: 1929 registered / 67 disabled / 1862 executed
       100% tests passed, 0 tests failed out of 1862        墙钟 299 s（真机串行）
```

即：**上游套件在 HarmonyOS PC 上以 1862/1862 全绿**，含全部"打开 MAMA"的用例
（中间件订阅/发布/队列/timer/transport、payload 编解码、field cache、MAMDA 订单簿与行情监听器等）。

- 上游 C#/Java 单元测试：需 .NET / JDK+gradle，平台不具备，`WITH_CSHARP/WITH_JAVA=OFF`
- 上游示例与测试工具（capturereplayc、capturec、mamalistenc、mamaproducerc 等）**全部构建成功并随包发布**（`bin/` 下 40+ 个）

### 4.2 已知限制（逐条给出归因）

1. **`bookviewer` 示例未构建**：唯一的 curses 依赖（MAMDA orderbooks 示例），本平台不引入 ncurses。
2. **3 个 x86 专用性能工具未构建**：`mamaconsumerc_v2`、`mamaproducerc_v2`、`mamapingpongc`（rdtsc 内联汇编 + glibc malloc 调优），非 x86 架构无法编译。
3. **CPU 亲和性**：用 `sched_setaffinity(pthread_gettid_np(thread), ...)` 等价实现（本平台没有 `pthread_setaffinity_np`），功能保留。
4. **无真实 AMQP broker**：上游单测只验证 API 层行为，不含 broker 进程；`bridge/qpid` 的连接是异步的，
   未连上 broker 不影响这些用例（全部通过），也不属于本包的适配缺陷。
5. **67 条上游用例被上游自身标记为 `DISABLED_`**（ctest 记为 Disabled，不执行），与本次适配无关。

## 5. 交付物清单

- 库：`libmama{,.a}`、`libmamacpp{,.a}`、`libmamda{,.a}`（含 book/news/options）、`libwombatcommon{cpp}{,.a}`
- 桥接/插件：`libmamabaseimpl.so`、`libmamanoopimpl.so`、`libmamaompbimpl.so`、`libmamaplugindqstrategy.so`、`libmamaentnoop.so`、**`libmamaqpidimpl.so`（AMQP 中间件桥）**、**`libmamaqpidmsgimpl.so`（qpidmsg payload）**
  - 上游 `bridge/qpid/CMakeLists.txt` 在 `INSTALL_RUNTIME_DEPENDENCIES` 打开时会把 `PROTON_LIBRARY_FILES` 一起装进 `lib/`，故包内另有 `libqpid-proton.so`；`package_info()` 同时声明 `qpid-proton` 为 Conan 依赖（消费者走 `conanrun` 也能解析到制品仓那份）
- 头文件：`include/mama`、`include/mamda`、`include/wombat`
- 工具：`bin/` 下示例与测试工具 40+ 个；`config/mama.properties`
