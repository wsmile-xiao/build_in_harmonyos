# taskflow 4.1.0 OHOS 适配说明

## 项目概况

- 上游：https://github.com/taskflow/taskflow（v4.1.0，tag tarball；SHA-256 见 conandata.yml / manifest.yaml）
- 类型：header-only C++20 库（CMake INTERFACE target），通用并行/异构任务编程系统（work-stealing 任务图）
- 许可证：MIT
- 依赖：无第三方依赖（仅标准库 + 线程）；W0 无外部依赖需要安装验证
- 包内容：`include/taskflow/`（70 个 `.hpp`）+ `licenses/LICENSE`；配方 `build()` 只做上游 CMake 项目的
  configure/build 一致性校验（INTERFACE 目标，不编译任何翻译单元、不产出二进制）

## 适配要点

### 1. header-only 打包（模板 `conanfile-headeronly.py.tmpl` 变体 A）

- `package_type = "header-library"`，`package_id()` 用 `self.info.clear()` 收敛为单一 package_id。
- `no_copy_source = True`，`layout()` 用 `basic_layout(src_folder="src")`。
- 头文件按 `taskflow/` 相对路径整体安装，保证 `#include <taskflow/taskflow.hpp>` 不变。
- `package_info()` 设置 `cmake_file_name=Taskflow`、`cmake_target_name=Taskflow::taskflow`，与上游
  `TaskflowConfig.cmake` 导出的 `find_package(Taskflow)` / `Taskflow::taskflow` 命名兼容。

### 2. C++20 下游要求（profile cppstd=17）

上游 `CMakeLists.txt` 强制 `CMAKE_CXX_STANDARD 20` + `CMAKE_CXX_STANDARD_REQUIRED ON`，头文件使用
C++20 concepts 与指定初始化器等特性；OHOS profile 固定 `cppstd=17`。包本身不编译任何翻译单元，
因此配方不做 `validate()` 拒绝，而是把要求下传给消费者：

- `cpp_info.cxxflags = ["-std=c++20"]`（CMakeDeps 生成的 target 会把该选项加入
  `INTERFACE_COMPILE_OPTIONS`，否则 cppstd=17 的消费者编译头文件即失败）；
- `test_package/CMakeLists.txt` 同时显式 `set(CMAKE_CXX_STANDARD 20)`，独立于生成器记录该要求。

### 3. OHOS libc++15 无 `std::pmr`：ObjectPool 后备分配器等价降级（patches/0003）

**实测现象**（设备 clang 15.0.4 + ohos-sdk_26.0.0.18）：

```
taskflow/utility/object_pool.hpp:6:10: fatal error: 'memory_resource' file not found
```

**根因**：OHOS SDK 的 libc++ 15 变体 `libcxx-ohos/include/c++/v1/` 不含 `<memory_resource>`
（全 SDK 只有 `experimental/memory_resource`），且 `libc++.so` 不导出任何 `std::pmr` 符号
（`nm -D --defined-only libc++.so | grep -c pmr` = 0，pmr 实现只存在于 `libc++experimental.a`）。
`experimental/memory_resource` 只提供 C++14 Library Fundamentals v1 的
`memory_resource` / `polymorphic_allocator`，**不含** `synchronized_pool_resource` 与
`pool_options`（实测编译该命名空间下的 pool 资源报 `no type named 'synchronized_pool_resource'`）。

taskflow 4.1.0 的 `tf::ObjectPool`（被 `tf::Graph` 用于节点池，是所有消费者的必经路径）在冷路径
成员上真实使用 `std::pmr::synchronized_pool_resource` + `std::pmr::pool_options`，因此不是
“守卫包含即可”的情况。

**适配**：`__has_include(<memory_resource>)` 特性探测（非平台条件编译），标准库具备 pmr 时仍走原生
`std::pmr`；不具备时改用库内自带的等价实现 `tf::SynchronizedBlockPool`：

- 互斥保护的固定块空闲链表 + 按 `max_blocks_per_chunk = 1024` 分块增长（保留上游文档描述的
  “一次加锁摊薄到整块”的冷路径摊销语义）；
- 对外只暴露 `allocate(bytes, alignment)` / `deallocate(p, bytes, alignment)` / `release()`
  三个 `ObjectPool` 实际调用的接口，调用点不改；
- 超过池化块尺寸或更严格对齐的请求直接走 `::operator new`，与 `polymorphic_allocator` 的上游
  回退行为一致；
- 是真实实现，不是空 stub；不改变 `ObjectPool` 的热路径（无锁 Treiber 栈）与公开 API。
- **异常安全**：`_grow()` 在 `::operator new` 成功后，若把 chunk 登记进 `_chunks` 时
  `std::vector` 扩容抛出 `std::bad_alloc`，会释放该 chunk 并重抛（不泄漏、不吞异常）；
  chunk 在链接空闲链表之前就已登记，`release()` 始终能看到本池持有的全部分配。

### 4. clang 15 不支持别名模板 CTAD：上游用例显式写出模板实参（patches/0001、0002）

**实测现象**：

```
unittests/test_iterators.cpp:180:18: fatal error: alias template 'IndexRange' requires
template arguments; argument deduction only allowed for class templates
```

**根因**：`tf::IndexRange` 是别名模板（`template <std::integral T> using IndexRange =
IndexRanges<T, 1>;`），C++20 的别名模板 CTAD（P1814）clang 至今未实现
（LLVM issue 106839，clang 15/16/17 同样报此错）。上游在 Clang 之外的工具链（GCC/MSVC/AppleClang）
上不受影响，属上游测试源的可移植性缺口。

**适配**：`test_iterators.cpp` 的 `IndexRange1D.CTAD` 用例与 `test_for_each.cpp` 两处
`tf::IndexRange range(...)` 改为 `tf::IndexRange<int>`。`test_iterators.cpp` 中该用例**同时改名**为
`IndexRange1D.alias_construction`（原名 `CTAD` 已不再反映实现，且避免误导后续读者以为仍在验证别名
CTAD 推导）；用例内保留原 `static_assert(std::is_same_v<decltype(r), tf::IndexRange<int>>)`，
因此**用例数、断言数、断言内容均不变**（ctest 注册表中 `IndexRange1D.alias_construction` 注册 1 项
并通过，`IndexRange1D.CTAD` 出现 0 次）。库头文件本身未使用该写法，只有 Doxygen 注释中的示例用了它。

### 5. 线程依赖

上游 INTERFACE target 链接 `Threads::Threads`。`package_info()` 在 `os in ("Linux", "OHOS")`
时声明 `system_libs = ["pthread"]`；OHOS SDK sysroot 提供 `libpthread.a`（musl 的 pthread 实现在
libc 内，`-lpthread` 为空归档），实测 `clang -lpthread` 链接正常，test_package 未额外 `find_package(Threads)`。

## 上游测试（设备端原生执行）

- 测试入口：上游 `unittests/`（内嵌 doctest，无外部依赖），CMake 配置 `TF_BUILD_TESTS=ON`（默认 ON）。
- 构建：设备原生 `cmake + clang 15.0.4`（`os=OHOS`、aarch64），`make -j1`，构建目录
  `$HOME/tmp/taskflow-4.1.0/native-build`，**34/34 个测试可执行全部构建成功（rc=0）**。
- 执行：`HOME=<沙箱>` 下 `ctest --output-on-failure -j1`，**2909 项注册用例全部通过
  （100% tests passed, 0 tests failed out of 2909）**，`Total Test time (real) = 334.59 sec`。
- 统计单位：ctest 注册的 doctest test case（`doctest_discover_tests` 按 `--list-test-cases` 注册）。
  与源码 `TEST_CASE` 行数并非严格 1:1——宏体展开的用例按实例化各注册一项（如
  `test_notifiers.cpp` 的 123 行 `TEST_CASE` 运行期展开为 194 项）：34 个已构建 target 的源码
  `TEST_CASE` 行数合计 2891，ctest 注册数 2909（+18）。本文件一律采用 ctest 注册口径。
- 取数命令：`ctest -N | grep -c 'Test *#'`（注册数=分母）；`ctest --output-on-failure -j1`（通过数=分子）。
- 本版本未修改任何库行为，仅 3 个可移植性补丁（见上），上游用例数、断言数与上游一致。

### 上游用例数口径（与审方数法对齐）

审方（pc-pr-review）按「含 `TEST_CASE` 字样的源码行」计数。本包据此声明：

| 口径 | 取数命令 | 数量 |
| --- | --- | --- |
| 上游合计（不含 vendored `3rd-party/`） | `grep -rh TEST_CASE unittests sandbox --include='*.cpp' --include='*.cu' \| wc -l` | **3606** |
| 其中 `unittests/**/*.cpp`（审方实测口径） | `grep -rh TEST_CASE unittests --include='*.cpp' \| wc -l` | **3246** |
| 其中 `unittests/**/*.cu` | 同上 `--include='*.cu'` | 256 |
| 其中 `sandbox/**/*.cu` | 同上对 `sandbox` | 104 |
| 设备端实跑覆盖 | 34 个上游默认构建 target 的源码行 | **2891** |
| 未执行 | 见下四组 | **715** |

自洽校验：`2891 + 715 = 3606`；`2891 + 355 = 3246`（`355 = 15 + 324 + 16`）。
运行期口径：2891 行由 `doctest_discover_tests` 展开为 **2909 个 ctest 注册用例**，全部通过
（源码行数与注册数非严格 1:1，宏体展开按实例化各注册一项，如 `test_notifiers.cpp` 123 行 → 194 项）。
`3rd-party/` 另有 60 行属 vendored 依赖（`doctest/doctest.h` 40、`tbb/src/test/` 20），不计入上游用例。
`examples/`、`benchmarks/`、`tfprof/`、`docs/`、`doxygen/` 的 `TEST_CASE` 命中实测均为 0。

### 上游默认未编译 / 上游已失效源（不计入 2909 的运行期分母，单列说明）

上游 `TF_BUILD_CUDA` / `TF_BUILD_MODULES` 默认 OFF，`test_serializer` 被上游注释，三项均不进入本轮
2909 的分母。按未打补丁的上游树实测清点（取数命令为 `grep -c 'TEST_CASE' <file>`）：

| 位置 | TEST_CASE 数 | 说明 |
| --- | --- | --- |
| `unittests/test_serializer.cpp` | 15 | 上游 `TF_UNITTESTS` 中以 `#test_serializer` 注释掉 |
| `unittests/cuda/`（全部 16 个 `.cu`） | 256 | 需 nvcc/CUDA 工具链；本设备无 CUDA，无法运行 |
| `unittests/cuda/`（上游 `cuda/CMakeLists.txt` 默认未注释的 7 个 target） | 76 | `TF_CUDA_UNITTESTS` 中仅 objects/basics/updates/matrix/kmeans/for_each/transform 未被注释 |
| `unittests/modules/test_cxx_modules.cpp` | 16 | `TF_BUILD_MODULES` 默认 OFF（需要 C++20 modules 工具链支持） |
| `unittests/test_deferred_pipelines.cpp` | 160 | 未接入任何 CMake 列表：不在 `TF_UNITTESTS` 内，也不被任何 CMakeLists 引用 |
| `unittests/test_deferred_scalable_pipelines.cpp` | 161 | 同上 |
| `unittests/test_priorities.cpp` | 3 | 同上 |
| `sandbox/cublas_unittests/*.cu` | 104 | 未被引用的测试子目录片段（helper 2 + level1 10 + level2 18 + level3 74），根 `CMakeLists.txt` 从不 `add_subdirectory`，依赖 cuBLAS/CUDA |

`test_deferred_*` 与 `test_priorities` 是上游从未接入构建的遗留测试源：全树 `grep -rl <name>`
除文件自身外 0 命中，设备构建目录也没有对应可执行文件（`ctest -N | grep -cE 'Deferred|Priorit'` = 0）。

**这些源对 4.1.0 已失效**（设备 clang 15 `-fsyntax-only` 实测，故上游自己也不编译它们）：

```
test_priorities.cpp:24:13: error: no member named 'priority' in 'tf::Task'
test_priorities.cpp:24:31: error: no member named 'TaskPriority' in namespace 'tf'
test_deferred_pipelines.cpp:41:21: error: no member named 'num_deferrals' in 'tf::Pipeflow'
test_deferred_scalable_pipelines.cpp:87:19: error: no member named 'num_deferrals' in 'tf::Pipeflow'
test_deferred_scalable_pipelines.cpp:95:18: error: no member named 'defer' in 'tf::Pipeflow'
test_serializer.cpp:576:22: error: no member named 'list' in namespace 'std'   （serializer 15 行，上游亦注释）
```

即：这 339 行（324 + 15）不是「跳过」，而是上游遗留源在当前 API 下无法编译；
cuda/sandbox 360 行需 nvcc/CUDA 工具链（本设备无），modules 16 行需打开 `TF_BUILD_MODULES`。
`sandbox/cublas_unittests` 是未被任何 CMake 列表引用的测试子目录片段（自带 `CMakeLists.txt`，
但无 `project()`/`cmake_minimum_required`，使用 `${PROJECT_NAME}`），
`grep -rn sandbox CMakeLists.txt unittests/CMakeLists.txt` 0 命中，且需要 CUDA 工具链。

清点边界：本表只统计「上游 unittest 体系（`unittests/` + `sandbox/`）内的 doctest TEST_CASE」；
`examples/`、`benchmarks/`、`tfprof/`（tag tarball 内只有 4 个前端文件，其 `server` 子目录是
未打进 tarball 的 submodule）、`docs/`、`doxygen/` 的 `TEST_CASE` 命中实测均为 0，故不计；`3rd-party/` 内的 60 处 `TEST_CASE`（vendored `doctest/doctest.h` 40、
`tbb/src/test/` 20）属第三方自带用例，同样不计。

未执行合计（本包按全量口径声明）：**最小 535**（15 + 76 + 16 + 324 + 104，cuda 只算上游默认会激活的
target）或 **全量 715**（15 + 256 + 16 + 324 + 104，cuda 计入目录内全部 `.cu`；与上文「未执行 = 715」一致）。
设备 `native-build/CMakeCache.txt` 实测 `TF_BUILD_CUDA=OFF`、`TF_BUILD_MODULES=OFF`，
与本表一致——未运行的原因是上游默认关闭或上游从未接入构建，不是漏跑。

### 上游测试原始日志摘录（正文可复核）

ctest 注册数（分母）：

```
$ cd $HOME/tmp/taskflow-4.1.0/native-build && ctest -N | tail -1
Total Tests: 2909
```

ctest 执行结论（分子）：

```
$ HOME=$HOME/tmp/taskflow-4.1.0/test-home ctest --output-on-failure -j1 | tail -3
100% tests passed, 0 tests failed out of 2909

Total Test time (real) =  334.59 sec
```

34 个测试可执行逐个直跑的 doctest 自报汇总（交叉复核口径，逐行见任务私有目录的
`doctest-direct-summary.txt`，34 行 rc=0 + 1 行 `DIRECT_DONE`）：

```
$ awk '{for(i=1;i<=NF;i++){if($i=="cases:"){t+=$(i+1);p+=$(i+3);f+=$(i+5);s+=$(i+7)}
         if($i=="assertions:"){a+=$(i+1);ap+=$(i+3);af+=$(i+5)}}}
       END{printf "test cases %d (passed %d, failed %d, skipped %d); assertions %d (passed %d, failed %d)\n",
                   t,p,f,s,a,ap,af}' doctest-direct-summary.txt
test cases 2909 (passed 2909, failed 0, skipped 0); assertions 429875936 (passed 429875936, failed 0)
```

完整日志留存于任务私有目录 `$HOME/tmp/taskflow-4.1.0/`（`upstream-ctest.log`、
`doctest-direct-summary.txt`、`doctest-test_*.log` × 34），同目录另存采信轮 `conan create`
日志副本 `conan-create-d3738c4.log`（17014 字节，sha256
`a2a23f7462f4af5387311b525da83bffe502d8afead2de0e8bff77fc67ee9f92`）。

### 两个统计口径（同一次设备执行）

| 口径 | 命令 | 结果 |
| --- | --- | --- |
| ctest 注册用例（=doctest test case） | `ctest --output-on-failure -j1` | 2909/2909 通过，0 failed，Total Test time 334.59 sec |
| 34 个可执行逐个直跑的 doctest 汇总 | 逐个运行 `unittests/test_*` | test cases 2909/2909；assertions 429875936/429875936，0 failed、0 skipped |

两条口径的分母一致（2909）且全部通过；取数命令与完整清单见 `test_package/MANIFEST.yml`。

## test_package（消费者验证）

`consumer.cpp` 用安装后的头文件独立编译（C++20，仅包含 `taskflow/taskflow.hpp` +
`algorithm/for_each.hpp` + `algorithm/reduce.hpp`——上游算法定义在各算法头中，伞头文件不含），
做 5 项真实断言，全部通过：

1. `tf::Executor(4)` 上跑 3 节点 DAG（`A.precede(B, C)`）→ 执行计数 == 3；
2. `executor.num_workers() == 4`；
3. `taskflow.for_each` 遍历 4096 个元素 → 访问计数 == 4096；
4. `taskflow.reduce` 求 0..4095 之和 → 精确等于 8386560；
5. 8 轮 × 5000 节点的大图 churn（每轮 `clear()` 回收）→ 执行计数 == 40000，覆盖
   `ObjectPool` 冷路径后备分配器的增长与回收（即 patches/0003 改写的代码路径）。

## 验证结果（设备端，2026-09-10）

- 原生构建：`make -j1`，34/34 测试可执行全部构建成功（rc=0）。
- 上游测试：`ctest --output-on-failure -j1` → **100% tests passed, 0 tests failed out of 2909**。
- `conan-verify taskflow 4.1.0` → **Verdict: PASS**（G0/G1/G2/G3 通过；
  `reports/conan-verify-report.md`）。
  - 报告同时给出 `G4 ⚠️ 无法找到程序包 ID` 与 `L2/L4/L5 ⏭️ 跳过（无 cache 路径）`——
    这是工作流第 7.2 节记录的 header-only（`package_id` clear）路径解析缺陷，按跳过对待，
    已人工补测并留证：`reports/conan-verify-supplement.md`
    （G4 包内 73 文件 = 70 头文件 + LICENSE + 2 元数据；L2 消费者真实编译运行 5/5；
    L4 PIE+NX+BIND_NOW/RELRO；L5 安装头文件与打补丁源码树逐字节一致，头文件聚合指纹 516fad50…、包内容聚合指纹 348a630f…）。
- `conan create`（`-pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
  --user=ohpcd --channel=stable`）：成功，日志 `reports/conan-create.log`。
- `test_package`：`RUN: "./consumer"` → `taskflow consumer OK: 5 checks passed
  (graph for_each reduce object-pool)`。
- 包产物：70 个 `.hpp` + `licenses/LICENSE`，无 `bin/`、无 `lib/`。
