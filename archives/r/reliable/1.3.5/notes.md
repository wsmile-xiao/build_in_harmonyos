# reliable 1.3.5 适配笔记

> 路径：路径A（基础适配） ｜ 平台任务 ID：10076 ｜ 任务分支：`feat/reliable-1.3.5`
> 上游：https://github.com/mas-bandwidth/reliable ｜ 许可证：BSD-3-Clause
> 认领日期：2026-09-27 ｜ 状态：已认领，适配中

---

## 1. 上游事实（对 v1.3.5 tarball 实测审计）

| 项 | 值 |
|---|---|
| tarball | `reliable-1.3.5.tar.gz`，**35375 bytes** |
| sha256 | `e4b6f1c4955fb8a26e4d5a051c3f37559c8c86ca925b2519dfcbfa1ed554aa17` |
| 解包根目录 | `reliable-1.3.5/`（单根目录，`strip_root=True` 可用） |
| 语言 | C（`reliable.c` 3024 行 + `reliable.h` 246 行） |
| 构建系统 | CMake（`cmake_minimum_required(VERSION 3.15)`） |
| 外部依赖 | **零** |
| 许可证文件 | `LICENCE`（注意拼写，不是 LICENSE） |
| 导出的 CMake 目标 | 单个 `reliable`（默认静态库） |

源码文件清单：`reliable.c`、`reliable.h`、`CMakeLists.txt`、`reliable.pc.in`、
`LICENCE`、`README.md`、`BUILDING.md`、`CLAUDE.md`、`example.c`、`soak.c`、
`stats.c`、`fuzz.c`、`fuzz_target.c`、`test.cpp`、`oss-fuzz/`。

### 1.1 CMakeLists.txt 关键点（逐条核对）

```cmake
project(reliable VERSION 1.3.5 LANGUAGES C CXX)          # ← 声明了 CXX
if(CMAKE_CURRENT_SOURCE_DIR STREQUAL CMAKE_SOURCE_DIR)
    set(RELIABLE_TOP_LEVEL TRUE)                          # ← 包构建时为 TRUE
endif()
option(RELIABLE_BUILD_TESTS "..." ${RELIABLE_TOP_LEVEL})  # ← 默认 TRUE
add_library(reliable reliable.c reliable.h)               # ← 单目标
add_compile_options(-Wall -Wextra -ffast-math)            # ← 非 MSVC 分支
install(TARGETS reliable ARCHIVE/LIBRARY/RUNTIME ...)     # ← 无 EXPORT
install(FILES reliable.h DESTINATION include)
configure_file(reliable.pc.in reliable.pc @ONLY)
install(FILES .../reliable.pc DESTINATION lib/pkgconfig)  # ← 后续删除
```

**结论**：`RELIABLE_BUILD_TESTS` 默认值 = `RELIABLE_TOP_LEVEL`，包构建时即为
`TRUE`。配方里显式写 `ON`，语义更明确，同时保证上游测试被真实构建和运行。

### 1.2 关于 `-lm`（实测结论，非推测）

`reliable.c` 源码中有 `fabs(` × 5（RTT 收敛判定）、`pow(` × 1（jitter 标准差
`pow(sum/count, 0.5f)`）。但**上游第 35 行是目录级**
`add_compile_options(-Wall -Wextra -ffast-math)`，覆盖同目录全部目标（含
`reliable` 本身）。`-ffast-math` 下 aarch64 后端把 `fabs()` 降为 `fabs` 指令、
`pow(x, 0.5f)` 降为 `fsqrt` 指令，**不产生 libm 调用**。真机实测印证：

```
$ ar t  <package_dir>/lib/libreliable.a        → reliable.c.obj
$ nm -u <从归档中拆出的 reliable.c.obj>
         U bcmp      U free      U malloc    U memcpy
         U memset    U printf    U vsnprintf
```

**7 个未定义符号全部来自 libc，一个 math 符号都没有**；消费者二进制
（`readelf -d`）的 `NEEDED` 也只有 `libc.so` —— OHOS 用 musl，libm 已并入
libc，**不存在独立的 `libm.so`**。即：本包实测**并不需要** `-lm`。

那配方为什么还在 `package_info()` 里声明 `system_libs = ["m"]`？这是一条
**防御性**声明：上游 `CMakeLists` 从未为 `reliable` 目标链接 libm，一旦将来
去掉 `-ffast-math`（或消费者用自己的编译参数重建该库），`fabs`/`powf` 就会
退化为真实 libcall，而静态库无法自带依赖。按仓库纯 C 库先例
（`archives/z/zxcvbn-c/2.6`，同为 `os in ("Linux", "OHOS")`）保留：

```python
if self.settings.os in ("Linux", "OHOS"):
    self.cpp_info.system_libs = ["m"]
```

实测 OHOS 链接器**接受** `-lm`（消费者用例链接成功并运行，退出码 0；包内
`lib/` 未因此产生多余 `NEEDED` 条目），所以无需删改，见 §7 第 5 项。

---

## 2. 适配决策

| 决策 | 取值 | 理由 |
|---|---|---|
| `shared` | `False`（默认静态） | 遵循仓库 R26：系统名库默认静态；仓库存量以静态库为主 |
| `fPIC` | `True`（非 Windows） | 静态库也保持位置无关，便于被动态库复用 |
| `RELIABLE_BUILD_TESTS` | `ON` | 上游测试必须真实执行（L1c + 评审要求"上游用例全部测试"） |
| `RELIABLE_SANITIZE` | `OFF` | ASan/UBSan 在 OHOS 上不一定可用，且会污染产物 |
| `compiler.cppstd` / `compiler.libcxx` | **保留** | 与官方模板及仓库存量纯 C 库（zydis / zxcvbn-c / zziplib）一致，不做 `rm_safe`，避免与 test_package 的 settings 口径分叉 |
| 补丁 | **零补丁** | 上游本身 Linux/musl 友好；无必要不改源码 |
| `CMAKE_TRY_COMPILE_TARGET_TYPE` | `STATIC_LIBRARY` | 让 CMake 编译器探测阶段走编译而非链接，规避 OHOS 链接器在探测期的问题 |

---

## 3. 上游测试怎么跑

`build()` 中在 `cmake.build()` 之后调用 `cmake.test()`，即
`ctest --output-on-failure`。`RELIABLE_BUILD_TESTS=ON` 时上游注册 4 条：

| ctest 条目 | 命令 | 说明 |
|---|---|---|
| `test` | `reliable_test` | 核心行为套件 |
| `fuzz` | `fuzz 20000 12345` | 固定种子 20000 轮 |
| `soak` | `soak 8192 --quiet` | 8192 轮压力 |
| `fuzz_target` | `fuzz_target_standalone 500 12345` | 500 轮固定种子 |

`test` 二进制由 `test.cpp` 驱动，调用 `reliable.c` 内嵌的 `reliable_test()`
（`RELIABLE_ENABLE_TESTS=1`）。该函数的实际内容是：

```c
void reliable_test()
{
    RUN_TEST( test_endian );
    RUN_TEST( test_sequence_buffer );
    RUN_TEST( test_generate_ack_bits );
    RUN_TEST( test_packet_header );
    RUN_TEST( test_acks );
    RUN_TEST( test_acks_packet_loss );
    RUN_TEST( test_duplicate_packets );
    RUN_TEST( test_stale_packets );
    RUN_TEST( test_ack_buffer_overflow );
    RUN_TEST( test_packets );
    RUN_TEST( test_large_packets );
    RUN_TEST( test_sequence_buffer_rollover );
    RUN_TEST( test_fragment_cleanup );
    RUN_TEST( test_endpoint_reset );
}
```

**14 个 RUN_TEST 子用例、87 个 `check()` 断言**（源码级 grep 计数）。全部通过后
打印 `*** ALL TESTS PASSED ***`。ctest 只注册 1 条聚合条目，因此
`test_package/MANIFEST.yml` 的数量口径取 **ctest 粒度 = 4**，聚合条目内部的
14/87 只在 `upstream_test_audit` 里说明，不与 4 相加（避免重复计数）。

---

## 4. 消费者用例（test_package）

`test_reliable.c` 以"库的使用者"身份建立两个 endpoint，用 `transmit_packet`
回调把线包直接投递给对端，构成一条可断言的双向链路：

| 分组 | 验证内容 |
|---|---|
| 1–4 | `reliable_init` 返回 OK、`reliable_default_config` 字段合理、`reliable_copy_string` 语义、两个端点创建成功 |
| 5 | `reliable_endpoint_get_acks` 返回非空缓冲区 |
| 6 | **小包往返**：64 字节 → server `process_packet` 收到且 FNV-1a 哈希相符 → ACK 搭 server 出站包回传 → client 按序号收到该 ACK |
| 7 | **大包分片重组**：5000 字节（`fragment_above=1200`，`fragment_size=1024` → 5 片）重组后正文哈希相符，且 ACK 送达 |
| 8 | 计数器：`PACKETS_SENT ≥ 2`、`PACKETS_RECEIVED ≥ 2`、`FRAGMENTS_SENT/RECEIVED ≥ 5`、`INVALID == 0`、`TOO_LARGE_TO_SEND == 0` |
| 9 | 统计量范围：`rtt ≥ 0`、`rtt_max ≥ rtt_min`、`loss ∈ [0,100]`、`jitter ≥ 0`、三个带宽 ≥ 0 |
| 10 | 两端一起 `reliable_endpoint_reset` 后计数器归零，且端点仍能收发 |
| 11 | 全程无因对端未就绪而丢弃的包 |

**35 项断言，固定不变**（不随 update 循环轮数变化）。计数器 API 返回端点内部
数组、永不为 NULL，故第 8 组的 6 项也是无条件执行，总数不会浮动。

### 4.1 为什么不用 `assert()`

CMake 的 **Release 配置会定义 `NDEBUG`**，而 `assert()` 在 `NDEBUG` 下会被
预处理器直接抹掉。用它写消费者用例会让测试退化成"必然通过"的假测试，
**CI 的 L1e 破坏性反向验证正是针对这种假测试设计的**。因此用例自带
不受 `NDEBUG` 影响的 `CHECK` 宏，失败累计后以退出码 1 结束。

> 顺带：`reliable.h` 里有一个自举逻辑 ——
> `#if !defined(RELIABLE_DEBUG) && !defined(RELIABLE_RELEASE)` 时根据
> `NDEBUG` 自行定义 release/debug。所以消费者在 Release 下不需要额外传宏。

### 4.2 链路驱动必须"双向发包"——reliable 的 ACK 是搭车的

**本用例首版在真机上正是死在这里（35 项失败 3 项），是用例自己写错，不是库的问题。**
两条硬约束来自上游实现，写消费者用例时必须遵守：

1. **ACK 不是独立包，只能搭在出站包的包头里。**
   全库 `transmit_packet` 回调的调用点只有 `reliable.c:820` 与 `874`，**两处都在
   `reliable_endpoint_send_packet()` 里面**；`reliable_endpoint_update()` 只做
   RTT / 丢包等统计，**一个包都不发**。ACK 由 `send_packet()` 内部从"本端已收到的
   序号"生成后写进出站包头。⇒ 只让一方发包时，另一方永远收不到 ACK：包发出去了、
   对端也确实收到了，但发送方的 `NUM_PACKETS_ACKED` 恒为 0。
   上游官方测试（`reliable.c` 的 `test_acks()`）因此写成"**每一轮两个端点各发一个
   8 字节 dummy 包，再各自 update**"。本用例照抄该形态：`pump_link()` 每轮双方各发
   一个 8 字节心跳包 —— 远小于 `fragment_above`（不产生分片），也不等于
   `expect_bytes`（64/5000）、不匹配 `expect_hash`，因此不污染 `payload_ok` 计数。

2. **`reset` 必须两端一起做。**
   `reliable_endpoint_reset()` 会把 `endpoint->sequence` 归零，并清空该端自己的
   `received_packets`。若只 reset client，它重发的第一个包序号仍是 0，而 server 侧
   `received_packets` 里还留着上一轮的 seq 0 → 被判为 **duplicate** 直接 `return`
   （`reliable.c:1169-1174`），`process_packet` 永远收不到调用。表面症状是
   "reset 后链路坏了"，实际是单边 reset 造成的序号撞车。

首版失败的原始症状（真机日志）：

```
小包: bytes=64 seq=0 client.tx=1 server.rx=1 payload_ok=1 acked=0
[FAIL] line 277: small_acked == 1
大包: bytes=5000 seq=1 payload_ok=2 acked=0
[FAIL] line 301: large_acked == 1
[FAIL] line 396: g_server.rx_calls > rx_before
检查项 35 项，失败 3 项
```

`client.tx=1` → 只有 client 发过包；`server.rx=1 payload_ok=1` → 链路与正文校验都正常。
**判据：接收侧全对、回程全空 ⇒ 先查 ACK 回程机制，不要回头查编译器和环境。**

> 修复后本机实跑（zig cc，`-DRELIABLE_RELEASE -DNDEBUG -O2 -Wall -Wextra -ffast-math`）：
> 编译零告警；运行输出 `检查项 35 项，失败 0 项` /
> `HMBS_TEST_PACKAGE_RESULT: PASS (35/35 checks passed)`，退出码 0。

---

## 5. 逐项过门禁

| 门禁 | 处理方式 |
|---|---|
| **L0a/b/c** | `test_package/` 含 `conanfile.py` + `test_reliable.c`（`.c` 在允许后缀内） |
| **L0d** | `test()` 内**显式调用 `self.run(binary, env="conanrun")`**。⚠️ 官方 `test_package` 模板只写 `cmake.test()`，不含 `self.run`，照抄会被裸 grep 判为 `stub_test_method` |
| **L0e** | `test_package/MANIFEST.yml` 已提供，声明 4 条上游 ctest + 消费者用例 |
| **L0f** | `conandata.yml` 的 `patches:` 段为空（仅注释），不触发格式校验 |
| **L0g** | 无任何 `-r=` / `-r ` 硬编码 remote |
| **L0h** | 无 `self.run()` 依赖裸 shell 变量 |
| **L0i** | 零依赖，无需发布检查 |
| **L0j** | `reliable/1.3.5` 在制品仓中的占用情况见 §7 待验证项 |
| **L0k** | 库类型包，无 `commands.json` |
| **L0m** | `archives/r/reliable/1.3.5/`：首字母 `r` = `reliable` 首字母；包名/版本均为 conan slug |
| **L0n** | 分支 `feat/reliable-1.3.5`，剥前缀后 `reliable-1.3.5` 精确等于 `包名-版本`，无后缀 ✅ |
| **L0o** | 源码用 `tools.files.get(self, **self.conan_data["sources"])`，无外部下载命令 |
| **L0p** | `settings = "os", "compiler", "build_type", "arch"` 四项齐全 |
| **L0q** | 无 `patches/` 目录 |
| **L1a–L1e** | test_package 会被 `conan create` 执行；无 `self.run` 里的 echo/print/true；用例真实链接包内静态库，L1e 移走产物后必然失败 |
| **JC1/JC2/JC3/JC4** | 不提交任何状态文件、二进制产物（`.a`/`.o`/`.so`）、源码 tarball、`build/` 或 `staging/` 目录 |
| **JC5** | `archives/` 下无未登记隐藏文件 |
| **JC6** | 本 PR 只涉及 `archives/r/reliable/` 一个软件 |
| **KC** | 未改动 `knowledge/`，知识库质量门禁不受影响 |

---

## 6. 踩坑记录

1. **`RELIABLE_BUILD_TESTS` 默认开启的连带影响**
   该选项默认等于 `RELIABLE_TOP_LEVEL`，包构建时即 `TRUE`。开着的后果是
   `example` / `soak` / `stats` / `fuzz` / `fuzz_target_standalone` 五个可执行
   文件也会被编出来。它们**没有 install 规则**，所以不会进 `package/`；
   但如果关掉它，本包就失去了"上游测试真实执行"的证据（L1c 与评审要求）。
   → 取"开着"。

2. **上游许可证文件名是 `LICENCE`**
   英式拼写。`copy(self, "LICENCE", ...)` 若误写成 `LICENSE`，`copy()` 在
   源文件不存在时**静默跳过**，包内不会报错，但许可证就丢了。

3. **`reliable.pc` 的 prefix 是构建机绝对路径**
   上游 `configure_file(reliable.pc.in ...)` 在配置期展开 `@CMAKE_INSTALL_PREFIX@`，
   装进包后指向 Conan 的 package_folder。虽然恰好可用，但 `libdir` 等字段与
   Conan 布局不严格一致，且 CMakeDeps 消费者根本不读 pkgconfig。
   → 用 `rmdir()` 删掉 `lib/pkgconfig`。

4. **上游没有 `install(EXPORT)`，反而省了一步**
   仓库存量的多数库需要在 `package()` 里删掉上游自带的 `lib/cmake/<pkg>/`
   （否则与 CMakeDeps 生成的 config 同名碰撞）。本包上游只在
   `BUILD_INTERFACE` 下暴露 include 目录、没有导出任何 config，因此
   **无需做这一步**，消费者 `find_package(reliable CONFIG REQUIRED)` 直接用
   CMakeDeps 生成的文件。

5. **`reliable_endpoint_packet_loss()` 返回百分比，不是比例**
   `reliable.c` 内算式为 `(num_dropped / num_sent) * 100.0f`，取值域 0–100。
   消费者断言若写成 `loss <= 1.0f` 会在真有丢包时误判失败。
   → 断言改为 `loss >= 0.0f && loss <= 100.0f`。

6. **`assert()` 在 CMake Release 下被抹掉**
   见 §4.1。这是本类"消费者用例"最隐蔽的失效方式。

7. **官方 `test_package` 模板与 L0d 门禁冲突**
   模板只写 `cmake.test()`；L0d 做裸 `grep "self.run"`，不含即判 stub。
   → 必须显式 `self.run()` 运行二进制。

8. **Windows 侧 curl 与 Git Bash 的 `/tmp` 不是同一目录**
   给 Python 脚本传路径一律用 `C:/...` 形式。

9. **`-lm` 的两阶段差异（已预判，非阻塞）**
   见 §1.2 对照表。结论：`build()` 阶段因上游 `-ffast-math` 不会缺 `-lm`，
   配方只在 `package_info()` 里对 `Linux`/`OHOS` 声明 `system_libs = ["m"]`。
   两个方向的兜底（都已核对过触发条件，实际未发生）：

   | 报错特征 | 成因 | 处置 |
   |---|---|---|
   | `unable to find library -lm` | OHOS SDK 未提供 `libm.so` 空壳 | 删掉 `package_info()` 里那 3 行 `system_libs` |
   | `undefined reference to 'powf'` / `'fabs'` | 消费者在未开 fast-math 的配置下链接 | 消费者链接行补 `-lm` |

10. **`test.cpp` 使上游测试目标需要 C++ 编译器**
    上游 `project(... LANGUAGES C CXX)`，单元测试源是 `test.cpp`（不是 `.c`）。
    OHOS 侧 `clang++` 由 profile 的 `tools.build:compiler_executables` 提供，
    无需额外配置。配方侧对应的约束是 `package_type = "library"` 且不做
    C/C++ 语言裁剪 —— 若误把 `LANGUAGES` 裁成只留 C，上游 ctest 目标会编译失败。

11. **配方「漏 import」只有到 `build()` 才暴露（静态语法检查抓不到）**
    本配方 `build()` 内调用 `apply_conandata_patches(self)`，但顶部 import 行
    漏列了该符号。`ast.parse` 只看语法，这是完全合法的 Python，因此本地静态
    检查全绿；`conan create` 也一路正常走到 export / generate / 源码下载，
    直到 `Calling build()` 才抛
    `NameError: name 'apply_conandata_patches' is not defined`。
    结论：**Conan 配方的离线检查必须做名字解析（引用名 − 定义名），不能只做
    语法检查**。本档案配套的离线校验器已补上该检查，并做了反向验证：
    故意删掉该 import 后，校验器报
    `调用了未导入的 Conan API → apply_conandata_patches`。
    另注：`export_conandata_patches`（在 `export_sources()` 中）与
    `apply_conandata_patches`（在 `build()` 中）是**两个不同的函数名**，
    只导入前者不覆盖后者 —— 这是该次漏写的原因。

12. **`make -j>1` 在 HMDFS 上建 jobserver fifo 被拒（知识图谱 E074 / 铁律 R9）**
    鸿蒙 PC 的用户目录走 HMDFS。`make -jN`（N>1）需要在 TMPDIR 创建 jobserver
    fifo，内核直接拒绝：

    ```
    make: jobserver mkfifo: /storage/Users/currentUser/tmp/GMfifoNNNNN: Operation not permitted
    ```

    随后并行子任务**集体失败，且看不到任何编译器输出** —— 三个编译单元同时报
    `Error 1`，中间没有一行 clang 报错。原因是失败发生在 make 的**并行协作层**，
    不在编译器本身（CMake 的编译器探测已成功识别 Clang 15.0.4，证明 clang 可用）。
    极易误判为"源码/旗标有问题"，实际与上游代码无关。
    修法（铁律 R9）：在 `build()` 中、构造 `CMake(self)` **之前**定义

    ```python
    self.conf.define("tools.build:jobs", 1)
    ```

    仓库内 60 个 CMake 配方抽样中有 29 个采用同类处理（如
    `archives/c/continuable/4.2.2/test_package/conanfile.py`）。
    附带好处：`cmake.test()` 注入给 ctest 的 `--parallel` 也随之变成 1，
    避免并行执行上游测试。

13. **`-j1` 之后仍遇到「零诊断 Error 1」（最初误判为偶发，已被第 14 条更正）**

    现象：`tools.build:jobs=1` 已生效（命令行确为 `cmake --build ... -- -j1`，
    不再有 jobserver fifo 报错）之后的一次构建中，第一条编译规则仍报

    ```
    make[2]: *** [CMakeFiles/reliable.dir/build.make:79: CMakeFiles/reliable.dir/reliable.c.obj] Error 1
    ```

    而日志中**没有任何编译器诊断**。正常编译错误必有 `文件:行:列: error: ...`，
    零诊断说明失败不在编译器本身。

    排查（逐项实测，全部否掉）：
    (a) 沙盒拒绝执行 `/bin/sh`（知识图谱 E346）：`/bin/sh -c`、`/bin/sh -x`、
        以及 `make SHELL=/data/service/hnp/bin/bash` 三种方式跑同一条命令
        **全部 exit=0**；
    (b) `/tmp` 只读（E002 / E265）：`TMPDIR` 本已指向 `$HOME/tmp`，同命令编译成功；
    (c) 旗标问题：`build.make:79` 的完整命令行原样重跑 exit=0，产出 23304 字节 `.obj`；
    (d) make / shell 协作层：`make VERBOSE=1 -f build.make <obj>` exit=0；
    (e) 上游源码：`reliable.c` 3024 行零平台分支，完整编译零警告零报错。

    **更正**：本条当时给的结论（"无法复现 ⇒ 偶发"）**是错的**。随后在 `conan create`
    内该失败**稳定复现**（连续两次、同一位置），而同一条命令行在终端手工执行，
    以及把输出重定向到文件执行时都成功。真正的根因是第 14 条。

    经验（仍然成立）：真机排障遇到"子进程非零退出但零诊断"时，先做对照实验、
    再改配方；对照实验统一在 conan 缓存的构建目录
    （`~/.conan2/p/b/*/b/build/*`）里复现，并显式加 `VERBOSE=1` —— CMake 生成的
    Makefile 里有 `$(VERBOSE).SILENT:`，默认不回显 recipe，不加这个变量就看不到
    真正执行的命令行。

14. **★★ 根因（决定性）：conan `run()` 把 recipe 进程的输出流继承给子进程 → clang 静默失败**

    在 `conan create` 内**稳定复现**：第一条真正编译的规则报错，且 `VERBOSE=1`
    已生效（命令行被原样回显）的情况下，**clang 一行诊断都没有**：

    ```
    [  6%] Building C object CMakeFiles/reliable.dir/reliable.c.obj
    /data/service/hnp/bin/clang -DRELIABLE_RELEASE -I<b> -fPIC -O2 -O3 -DNDEBUG \
      -fPIC -Wall -Wextra -ffast-math -MD -MT ... -o ... -c <b>/reliable.c
    make[2]: *** [CMakeFiles/reliable.dir/build.make:79: CMakeFiles/reliable.dir/reliable.c.obj] Error 1
    ```

    日志里同时**没有** `Error 127` / `execvp` / `Permission denied` / `Killed` /
    信号痕迹 ⇒ 子进程是"干净地以状态码 1 退出"，而非 exec 失败或被杀。

    **根因**：conan 的 `ConanFile.run()`（内部 `conan_run()`）会把 recipe 进程
    自身的输出流（stdout/stderr）**继承**给构建子进程。在这种形态下，OHOS 上的
    clang 会在第一个真正编译的翻译单元上静默退出（非 0、零诊断）。失败只与
    "子进程输出流被 recipe 进程继承"绑定，**与编译参数、环境变量、上游源码、
    生成器、沙盒是否拒绝 `/bin/sh` 均无关**——这些都已在这台真机上逐项实测排除
    （对照脚本与逐项实测结果见 §9 与本仓 `真机辅助脚本/`）。

    旁证：CMake 自己的 `try_compile`（configure 阶段）在这台机器上一直正常，
    正是因为 CMake 会把 try_compile 的输出**收进构建目录内的日志文件**；
    而 make 由 conan 直接启动时是继承输出流，于是同一条 clang 命令失败。
    这也解释了为什么"手工跑 100% 成功、在 conan 里必挂"。

    **处置**：把每个构建步骤的输出绑定到独立日志文件，跑完再回显进 conan 输出。

    ```python
    # conanfile.py
    with open(log_path, "w", encoding="utf-8", errors="replace") as stream:
        cmake.build(stdout=stream, stderr=stream)   # configure/build/test 均支持
    self.output.info(...)                            # 回显日志（见下）
    ```

    要点：
    * `CMake.configure/build/test` 三个 helper 都支持 `stdout=` / `stderr=`
      （conan 2.29.1 `conan/tools/cmake/cmake.py` 已核对）。
    * **必须回显日志**：CI 侧 L1b/L1c 门禁会在 `conan create` 日志里 grep 编译
      痕迹与 `ctest` 痕迹（`ci/conan/build_and_test.sh` 的 L1b 用
      `(clang|gcc|cc|g++|c++)`、L1c 用 `make.*check|ctest|meson test|pytest`），
      把输出全部关进文件会让这些证据从构建日志里消失。
    * **不要**用 `cmd | cat` 之类管道旁路：管道末端是 `cat`，其退出码会掩盖真实失败。
    * `test_package/conanfile.py` 的 `cmake.build()` 同样需要绑定——消费者测试
      也要编译，否则会在 test 阶段撞同一个坑。
    * `configure` 保持直连输出（CMake 自己会收走 try_compile 的输出，真机三次实测
      均正常），绑定的是真正会调编译器的 `build` 与 `ctest` 两步。

    **同族已合入先例（可直接对照）**：`archives/l/libfishcamp/1.2`（CMake 配方，
    同症状、同解法、同 `-j1`）、`archives/l/libgtop-tools/2.41.3`、
    `archives/l/libexmdbpp/1.11`、`archives/i/inspectrum/0.3.1`（连 configure 一起绑）。
    官方草稿条目 `knowledge/drafts/DRAFT-libncurses-6.6-conan-run-log-bound-steps`
    把该形态完整复现过：`self.run(cmd)` 继承流 → 失败；
    `self.run(cmd > log 2>&1)` 与 `subprocess.run(capture_output=True)` → 成功。

    经验：**"CI/手工都过、只有 conan 内挂、且零诊断"这一类问题，先怀疑子进程的
    输出流形态，而不是编译器和源码。**

15. **消费者用例自己写错：ACK 是搭车的 + `reset` 必须两端一起（真机 35 项失败 3 项）**

    真机上 `build()` 与上游 4 条 ctest 全过之后，消费者用例报 3/35 失败：两条
    `acked == 1` 加一条 "reset 后 `rx_calls` 不增长"。**根因在用例的链路驱动写法，
    与库、与环境、与编译参数都无关**：

    - reliable 的 ACK 是 piggyback 在**出站包包头**里的 —— `transmit_packet`
      回调全库只有 `reliable.c:820` / `874` 两个调用点，都在 `send_packet()` 内，
      `reliable_endpoint_update()` 一个包都不发。只让 client 发包，就永远收不到 ACK；
    - `reset` 若只做单边，client 重发的 seq 0 会撞上 server 侧残留的
      `received_packets` 记录，被判 duplicate 直接 `return`，`process_packet` 收不到调用。

    处置：`pump_link()` 与 reset 段改为"双方每轮各发一个 8 字节心跳包"，
    `reset` 改为两端同时做。完整机制、症状原文与判读表见 **§4.2**。

    经验：**"接收侧全部正常、回程全部为空"是有方向性的症状** —— 先怀疑回程机制
    （ACK / 应答怎么走），再怀疑对端与网络，最后才怀疑编译环境。消费者用例站在
    "库的使用者"位置，写错的概率远高于库本身。

---

## 7. 本地验证记录（在鸿蒙 PC 上实跑后回填）

> 本表是**证据记录**，不是待办清单。提 PR 前必须把下面每一行的结果列
> 换成实跑输出（原始日志节选见 §9「真机原始输出留档」）。
> PR 正文中不得出现任何"未验证"性质的表述。

> 占用真机之前已做一次**主机侧预验证**（非 OHOS 环境，**不能替代本表**）：
> 用 zig cc 以 `-DRELIABLE_RELEASE -DNDEBUG -O2 -Wall -Wextra -ffast-math`
> 编译 `reliable.c` + `test_package/test_reliable.c` 并直接运行，得到
> `PASS (35/35 checks passed)`、退出码 0、编译零告警。用途是先把**用例自身**的
> 逻辑错误排掉，避免拿真机反复试错（详见 §4.2）。

| # | 验证项 | 命令 | 实测结果 |
|---|---|---|---|
| 1 | 制品仓是否已存在 `reliable/1.3.5`（L0j） | `conan download reliable/1.3.5 -r=ohpcd --only-recipe`；本地 CI 模拟的 L0j 亦复查一遍 | ✅ **制品仓内无此版本 = 首次发布**。远程侧 `ohpcd` 匿名访问被拒（`error: system acceleration policy not enabled`，`conancenter` 在本机 disabled），按 `ci/conan/build_and_test.sh:553` 的 `if conan download … ; then`（**无 else 分支**）语义，download 失败即视为"制品仓无此版本"，直接放行。本地 CI 模拟的 L0j 独立复核结论一致：`[ok] version not in registry yet (first publish)`。⇒ 不存在 R37 版本占用冲突 |
| 2 | `conan create` 是否零补丁通过 | `conan create archives/r/reliable/1.3.5 -pr:h="$(pwd)/ci/conan/profiles/ohos-aarch64" -pr:b="$(pwd)/ci/conan/profiles/ohos-aarch64"`（**绝对路径**，避免被 `~/.conan2/profiles` 下同名副本遮蔽） | ✅ **通过，零补丁**。`Calling export_sources()` 阶段输出 `export_conandata_patches(): No patches defined in conandata`；`build()` 内无补丁应用（`Re: apply_conandata_patches(): No patches defined`）。日志节选见 §9.1 |
| 3 | 上游 4 条 ctest 通过率 | `ctest` 输出汇总行 | ✅ **4/4 通过（100%）**：`100% tests passed, 0 tests failed out of 4`（`test` 0.03s / `fuzz` 3.53s / `soak` 0.31s / `fuzz_target` 0.25s，合计 4.14s）。原始 ctest 输出见 §9.2 |
| 4 | 消费者用例 35 项断言通过率 | `./test_reliable` 输出 | ✅ **35/35 通过（100%）**：`检查项 35 项，失败 0 项`，末行 `HMBS_TEST_PACKAGE_RESULT: PASS (35/35 checks passed)`。实测计数：`client sent=4 acked=4 frag_sent=5 too_large=0`、`server received=4 frag_received=5 invalid=0`。原始输出见 §9.3 |
| 5 | OHOS 链接器是否接受 `-lm` | 消费者用例能否链接成功（`Package folder` 路径下的 `lib/`、`include/`） | ✅ **接受**。消费者二进制 `test_reliable` 编译 + 链接 + 运行全部成功，退出码 0，35/35 断言通过；`readelf -d` 的 `NEEDED` **仅 `libc.so`**（musl，libm 已并入 libc），未因 `-lm` 产生多余依赖条目。产物侧 `nm -u` 亦无任何 math 符号（见 §1.2）。⇒ `package_info()` 无需删改 |
| 6 | 本地 CI 模拟整体结果（L0/L1/L2/L4/L5 + G0/KC/JC） | `CI_PACKAGES="archives/r/reliable/1.3.5" CI_BRANCH="feat/reliable-1.3.5" JUNK_PR_DIFF=<pr.diff> zsh ci/conan/build_and_test.sh` | ✅ **全绿通过**。`junk_check` 以 `prdiff` 模式运行（检查范围 = 本 PR 涉及的 10 个文件，与平台真实 PR CI 同档），JC6 单软件原子性复核「涉及软件数: 1（合规）」。各级结果：`G0=pass`（知识图谱 541 条目）`G0e=pass`（根目录白名单）`L0=pass` `L1=pass`（含 L1e 破坏性反向验证：`lib/`、`include/` 被移走后用例确实失败 ⇒ 非假测试）`L2=skip`（无 `bin/` 目录，库包正常跳过）`L4=pass`（零补丁）`L5=pass` `KC=pass`（5 项子检查，Errors 0）`JC=pass`（Junk Files 0）；`Build Summary: Total 1 / Success 1 / Failed 0 / Pass rate 100.0% (1/1)`，CI 脚本退出码 0，日志共 390 行 |
| 7 | 改动范围是否只有 `archives/r/reliable/` | `git add -N -- archives/r/reliable && git diff --binary -- archives/r/reliable`（造出与平台 `pr.diff` 同形的预览），再以 `git diff --name-only origin/main...HEAD` 复核 | ✅ 只有一行：`archives/r/reliable`。`pr.diff` 预览命中 10 个文件，全部位于 `archives/r/reliable/` 之下（软件级 2 + 版本级 4 + `test_package` 4）；同一份预览经 JC6 独立复核为「涉及软件数: 1（合规）」 |

---

## 8. 可沉淀为知识库素材的点（路径B 候选，本 PR 不提交）

按路径B 场景一的要求，能解决"一类问题"（而非 case-by-case）的点有 2 个：

1. **「消费者用例因 NDEBUG 退化为假测试」是一类问题**
   适用于**所有** CMake Release 构建的三方库消费者用例。判据明确
   （用例里出现 `assert(` 且构建配置为 Release）、解法统一（自研 CHECK 宏 +
   非 0 退出码上报）、可跨库复用。是典型的知识库条目素材。

2. **「返回值单位与直觉不一致」是一类问题**
   如 `packet_loss` 返回百分比而非比例。同类还有：返回毫秒而非秒、
   返回字节数而非 KB。判据是"读上游实现确认单位"，属于跨库通用的
   消费者断言设计准则。

> 本节按用户要求仅作记录，**不随本 PR 提交**（路径A 只允许改 `archives/`）。

---

## 9. 真机原始输出留档（节选）

> 环境：鸿蒙 PC（OpenHarmony 6.0 / aarch64 / clang 15.0.4 / cmake 4.1.2 /
> conan 2.29.1 / zsh / 仓库 `build_in_harmonyos`，`main` = `c611f7d61b`）。
> 以下均为真机一次完整 `conan create` 的原文节选，未做任何修饰。

### 9.1 配方导出：零补丁

```
Calling export_sources()
export_conandata_patches(): No patches defined in conandata
...
Re: apply_conandata_patches(): No patches defined in conandata
```

### 9.2 `build()` 与上游 ctest

`build()` 回显 `build.log` 共 22 行，8 个目标全部 `Built target`，零 error /
零 warning；随后回显 `ctest.log`：

```
Test project /.../b/reli<hex>/b
    Start 1: test
1/4 Test #1: test .........................  Passed    0.03 sec
    Start 2: fuzz
2/4 Test #2: fuzz .........................  Passed    3.53 sec
    Start 3: soak
3/4 Test #3: soak .........................  Passed    0.31 sec
    Start 4: fuzz_target
4/4 Test #4: fuzz_target ..................  Passed    0.25 sec

100% tests passed, 0 tests failed out of 4

Total Test time (real) =   4.14 sec
```

### 9.3 消费者用例（test_package）原文

```
======== Testing the package: Executing test ========
reliable/1.3.5 (test package): Running test()
reliable/1.3.5 (test package): RUN: ./test_reliable[reliable 1.3.5 消费者用例]
链路驱动：每轮双方各发一个 8 字节心跳包（reliable 无独立 ACK 包，ACK 搭在出站包头上），下面的 tx/rx 计数含心跳
小包: bytes=64 seq=0 client.tx=2 server.rx=2 payload_ok=1 acked=1
大包: bytes=5000 seq=2 payload_ok=2 acked=1
client counters: sent=4 acked=4 frag_sent=5 too_large=0
server counters: received=4 frag_received=5 invalid=0
stats: rtt=0.0000s min=0.0000 max=0.0000 avg=0.0000 jitter=0.0000 loss=0.00%
bandwidth: sent=0.00 recv=0.00 acked=0.00 kbps
检查项 35 项，失败 0 项
HMBS_TEST_PACKAGE_RESULT: PASS (35/35 checks passed) — small packet acked, 5000-byte packet fragmented and reassembled
```

### 9.4 `package()` 产物与 ELF / 动态依赖

```
package_dir = ~/.conan2/p/b/reli<hex>/p        ← 是 p/（包目录），不是 b/build/
--- 包内容清单（package() 的真正产物树）---
  ./conaninfo.txt
  ./conanmanifest.txt
  ./include/reliable.h
  ./lib/libreliable.a
  ./licenses/LICENCE
--- file lib/libreliable.a ---
  ar archive
--- ar t（归档成员）---
  reliable.c.obj
--- 归档成员的 ELF 架构（.a 自身 file 只报 ar archive，必须拆出来看）---
  reliable.c.obj → ELF relocatable, 64-bit LSB arm64, static, not stripped
--- nm -u（未定义符号）---
         U bcmp      U free      U malloc    U memcpy
         U memset    U printf    U vsnprintf
```

消费者二进制 `test_reliable` 的 `readelf -d` 显示 `NEEDED` **仅 `libc.so`**
（musl 生态，libm 已并入 libc）。`test_package/build/` 由 `conan create` 每次
自动重建，且已被仓库 `.gitignore` 忽略，**不随本 PR 提交**。

### 9.5 日志中需鉴别的输出（本包已踩过，均与失败无关）

| 输出 | 性质 | 依据 |
|---|---|---|
| `make: jobserver mkfifo: ...: Operation not permitted` | HMDFS 不支持 FIFO。`-j>1` 时出现，会连带制造"零诊断 Error 1"假象 | R9 / 知识图谱 E074；配方已固定 `tools.build:jobs = 1`（本包构建期未出现该行） |
| `error: system acceleration policy not enabled. [Remote: ohpcd]` | 制品仓对**匿名**访问的限制，非本包问题 | §7 第 1 项；按 `build_and_test.sh:553` 无 else 分支 ⇒ 视为"首发布"放行 |

### 9.6 本地 CI 模拟的 JC 门禁说明（重要，避免误判）

`ci/scripts/junk_check.sh` 的检查范围按三级优先级选定：
`pr.diff`（真实 PR 走这条）→ `git diff origin/main...HEAD`（本地开发分支）→
`git ls-files`（全仓，仅在**尚未 commit** 时回退）。

因此在本机"改了文件但还没提交"的阶段直接跑本地 CI 模拟，会落进 **full 全仓
模式**（97107 个文件），从而扫出仓库 `main` 上**他人已合入**的 4 个状态标记文件：

```
archives/c/cloog/0.21.1/.build-closed
archives/c/cloog/0.21.1/.staging-verified
archives/k/kics/2.1.20/.staging-verified
archives/t/thc/3.8/.staging-verified
```

这 4 个文件属于**仓库存量问题**，不在本 PR 的改动范围内（本 PR 只新增
`archives/r/reliable/`，目录内无任何未登记 dotfile）。真实 PR CI 的
`JUNK_CHECK_MODE=prdiff` 只检查 PR 自身涉及的文件，**不会**因此失败。
