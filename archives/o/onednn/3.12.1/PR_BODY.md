- **三方库名称**：onednn（oneAPI Deep Neural Network Library / oneDNN）
- **上游版本**：3.12.1（tag `v3.12.1` = `c8c37fdbecb5aa4dcf5ea7e77fba0fd1a98bd16f`，
  tarball sha256 `e1db6e9c3771ba137a6e9292c31870471362977760d0ca00adef2fd39e23840b`）
- **上游仓库地址**：https://github.com/uxlfoundation/oneDNN
- **适配路径**：路径 B（贡献创新）
- **使用知识库**：无可复用的既有条目解决本次阻塞点（0 命中口径见「补充说明 5」）。本次新增 1 组成对草稿
  `DRAFT-onednn-3.12.1-musl-sysconf-cache-keys-unavailable`（机制类，
  `knowledge/drafts/DRAFT-onednn-3.12.1-musl-sysconf-cache-keys-unavailable.{kv,md}`，
  `draft: true`、`contributor_id: iKalous_OscarP`）：OHOS musl 的 confname 表里有 141 个 `_SC_*`
  却 **0 个 `_SC_LEVEL*`**，真机也没有 `/sys/devices/system/cpu/cpuN/cache` 拓扑目录，
  于是「字典 → sysfs → sysconf」三级缓存探测在前两级空、第三级**连宏名都不存在**，
  表现是编译期 `use of undeclared identifier` 而不是运行期取不到值；把宏名伪造补上会让
  `sysconf()` 统一返回 `-1`/`errno=22(EINVAL)`（实测），把显式编译错误降级成隐式运行期错值。
  推荐修法为 `#ifdef _SC_*` 存在性守卫（main 里 `archives/p/pxr-vt/26.08` 已是该形态），
  配方内 `replace_in_file` 写死常量是本库采用的回退形态。关联 issue：**#3156**（同标题前缀，双向关联）。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1651 | 来源：`tests/`（实际全部落在 `tests/gtests`，`tests/benchdnn` 内 0 个 TEST 宏）。取数（最大口径，防「少报」）：`grep -rhoE '\b(INSTANTIATE_TEST_SUITE_P\|INSTANTIATE_TEST_CASE_P\|TEST(_P\|_F)?)[[:space:]]*\(' tests \| wc -l` → **1651**。同口径只数 `TEST/TEST_F/TEST_P` 宏为 **1477**（`grep -rhoE '\bTEST(_P\|_F)?[[:space:]]*\(' tests \| wc -l`），仅 `tests/gtests/**/*.cpp` 为 **1469**；含 `#if 0` 屏蔽块（grep 不解析条件编译）。三者均已列出，本表声明取上界 1651 |
| 集成测试 | 0 | `tests/benchdnn` 是独立基准/校验套件（`.ini` 输入 + 自研 driver，0 个 gtest 宏、不注册 ctest 用例），本配方按 3.13 范本注释掉其 `add_subdirectory`，不计入用例数 |
| 其他测试 | 0 | `tests/api` 与 `tests/regression` 已包含在上表的 `tests/` 递归口径内，无额外套件 |
| **合计** | **1651** | ctest 注册数与二进制数：`ctest -N` → **63**（一个 `TEST_P` 模板宏在实例化后对应多个运行期用例，故二进制数 63 ≪ 宏数 1651，两者不是同一层口径） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1651 | 不变 | `ONEDNN_BUILD_TESTS=ON` + `DNNL_BUILD_TESTS=ON`，63 个 gtest 二进制全部构建并在真机 `ctest` 内**真实执行**，未用 `-E`/`--exclude`/`--gtest_filter` 排除任何一条；结果 60 通过 / 3 未通过（原因逐条见「未通过项」） |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 12 | 新增 | `test_package/test.c` 消费者断言 12 项（链接已发布的 `libdnnl.so`，在真机运行）：CPU engine 创建、`dnnl_version()` 与已安装头文件 `DNNL_VERSION_{MAJOR,MINOR,PATCH}` 一致、memory descriptor 与字节数、softmax forward 的 pd/primitive/stream/memory 绑定、`dnnl_primitive_execute` 真跑 AArch64 JIT、每个通道切片和为 1、两个元素与本地 `expf` 参考值一致。取数：`grep -cE '^[[:space:]]+CHECK\(' test_package/test.c` → **12**（注意 `grep -c 'CHECK('` 得 13，多算了 `#define CHECK` 定义行）；真机运行输出 `12/12 assertions passed` |
| **合计** | **1663** | **+12** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

1. **修改的测试文件**：`tests/CMakeLists.txt`（配方 `source()` 内 `replace_in_file`）
   - **修改原因**：`add_subdirectory(benchdnn)` 会把基准套件一起编出来，单轮 `conan create`
     时长翻倍且不提供任何 gtest 用例；OHOS 上它的运行依赖（外部分组参考数据）也不具备
   - **修改内容**：仅把该行注释为 `# add_subdirectory(benchdnn)`。**未删除、未跳过任何上游
     测试用例**：`tests/benchdnn` 内 `TEST/TEST_F/TEST_P` 宏计数为 0，也不向 ctest 注册用例，
     所以 63 个 ctest 二进制与 1651/1477/1469 三个口径的用例计数完全不受影响

2. **修改的非测试文件**：`third_party/xbyak_aarch64/src/util_impl_linux.h`（同类，一并说明）
   - **修改原因**：OHOS musl 未定义 `_SC_LEVEL*_CACHE_SIZE` 系列 confname，该分支编译失败
   - **修改内容**：把 sysconf 兜底分支的 4 行赋值换成常量；机制、更优的守卫式修法与
     「伪造宏名会变成 -1/EINVAL」的实测反证，见本 PR 的知识草稿

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

鸿蒙特有测试（12 项）是 Conan 消费者契约（打包件能否被下游链接、运行、版本自洽、
AArch64 JIT 真跑），不替代也不计入上游 gtest 套件。

## 验证结果

- 编译状态：通过（`conan create` 退出码 0）
- 上游测试用例通过率：60/63 二进制（95.2%；未通过 3 项逐条技术原因见下，声明分母口径 1651 见上表）
- 新增测试用例通过率：12/12（100%）

真机取证（HarmonyOS PC aarch64，ohos-sdk 26.0.0.18 / clang 15.0.4 / musl，
独立 `CONAN_HOME=~/work/psj/ch-onednn`，不触碰共享缓存）：

```
$ conan create archives/o/onednn/3.12.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
CREATE_EXIT:0
95% tests passed, 3 tests failed out of 63
Total Test time (real) = 2600.11 sec
The following tests FAILED:
	 15 - test_eltwise (Timeout)
	 40 - test_reorder (Failed)
	 57 - test_api (Timeout)
Errors while running CTest
onednn version=3.12.1 engine=cpu ok: 12/12 assertions passed     # test_package
```

配方 rev `29fdb6dfdc6b13404a7eef654119d1fd`、包ID `01d92cf349a0dd98ff915f4bd99a04430171517f`、
包 rev `abab0793a59d6689e43559a6e7e794c3`；产物 `p/lib/libdnnl.so`（60308096 B，
`ELF 64-bit LSB arm64`，NEEDED 仅 `libc.so` / `libc++_shared.so` / `libomp.so`）+ 26 个安装头。

### 未通过项的具体技术原因（3 项，与已合入 3.13 的 5 项相比已缩小）

1. `test_reorder`（Failed，4.07s）：该二进制内 `[==========] 237 tests from 13 test suites ran`，
   失败的是其中 **12 个 `PaddedWeights_CPU/reorder_simple_test_t_f32_f32.TestsReorder/{4,8,12,14,18,20,22,24,26,30,34,36}`**。
   它们校验 x64 的 padded/blocked 权重重排（`nChw16c`/`OIWp16c` 一类带 padding 的 16 元素微内核布局）。
   AArch64 JIT 没有对应的 padded weights 布局，`src/cpu/aarch64` 不实现这些格式，
   期望值本身是 x64 ISA 产物 —— 无法靠配方在 aarch64 上变成 PASS（同 3.13 的判定）。
2. `test_eltwise`（Timeout，600s 截断）：`Test_Eltwise_EF/eltwise_test_t.TestsEltwise/*` 的
   TEST_P 实例数量极大（同一模板对多算法 × 多数据格式 × 多尺寸组合），600s 内只推进到
   第 9 个 `[ RUN ]`（`EltwiseSimpleF32/.../0`）。属**时长**问题，不是断言失败。
3. `test_api`（Timeout，600s 截断）：600s 内推进到第 23 个 `[ RUN ]`，卡点是
   `AllEngineKinds/engine_test_t.TestMultithreading/0` —— 对所有 engine 类型组合做并发压测，
   在 8 核 + OpenMP 顺序展开下超过单用例预算。同为**时长**问题。

两个 Timeout 保留在套件内（没有 `-E` 排除、没有调小 `--timeout` 让它「看似通过」），
按 ctest 真实结论记录为未通过。完整复现：

```
cd <build>/build/Release
env LD_LIBRARY_PATH="<build>/build/Release/src:$HOME/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/lib" \
    OMP_NUM_THREADS=4 ctest --output-on-failure --timeout 600
ctest -N                      # 63 个注册用例
```

## 补充说明

1. **构建配置**：AArch64（`DNNL_TARGET_ARCH`/`ONEDNN_TARGET_ARCH`/`CMAKE_SYSTEM_PROCESSOR`
   三处显式指定，否则 CMake 探测落到 X64 并加 `-msse4.1`）、`CPU_RUNTIME=OMP`
   （`ONEDNN_*` 与 `DNNL_*` 双前缀，由 `cmake/dnnl_compat.cmake` 互通）、
   `ENABLE_WORKLOAD=TRAINING`、`GPU_RUNTIME=NONE`、`AARCH64_USE_ACL=OFF`、`BUILD_GRAPH=OFF`、
   `CMAKE_POSITION_INDEPENDENT_CODE=ON`、`ARCH_OPT_FLAGS=""`。
2. **musl 差异**：`_SC_LEVEL*_CACHE_SIZE` 不存在 → sysconf 兜底分支写死 L1i/L1d 32KiB、
   L2 256KiB、L3 0（详见知识草稿，含真机 7 组实测数字与两种修复形态的取舍）。
3. **源码获取**：`conandata.yml` 的 `sources.url` 保持**单值**官方地址（不写第三方镜像、
   不用 list，避免关掉 CI 的镜像注入）。真机到 `github.com` 出现
   `ConnectTimeout (connect timeout=30)`，故真机侧用配方自带的 `OHC_TARBALL` 离线注入；
   URL 内容与 sha256 已由「本机两种 URL 形式 + 真机 curl 同一 URL」三方对拍为
   `e1db6e9c…3840b`，与 `conandata.yml` 逐字符一致。
4. **时长预算**：真机（与其他会话共享 8 核）单轮 `conan create` ≈ 编译 1900s +
   `ctest` 2600s。曾评估 `ctest -j4` 以压墙钟，实测每个二进制的自身耗时约翻倍
   （`test_reorder` 4.07s → 8.63s），会把 `test_gemm_bf16bf16f32`（顺序 475.45s）这类
   长用例推入 600s 超时、**新增**失败项，故保留与已合入 3.13 完全相同的顺序 ctest 形态
   （该形态在 CI worker `REL-001` 构建 #7342 上已验证通过）。
5. **路径 B 的 0 命中反证**（按 main tip `8f56191952c22d8f024ac0ebabaab5b4a52b19c7` 重测）：
   `knowledge/graph/E[0-9]{3}.kv` 540 条、`knowledge/drafts/*.kv` 1316 个，
   `git grep -ilE '_SC_LEVEL|ICACHE_SIZE|cpu0/cache' <tip> -- knowledge | wc -l` → **0**；
   `git grep -l 'sysconf' <tip> -- knowledge/graph` 只命中 E036（Python `sysconfig` 平台串含空格）
   与 E465（ctypes/dlopen 被 worker loader 拒载），二者均与 confname 宏存在性无关，
   边界与反证命令写在草稿 `.md` 的「查重反证」段。
6. **已知限制**：`libc++_shared.so` 与 `libomp.so` 由 OHOS SDK 目录经 profile 的
   `[buildenv] LD_LIBRARY_PATH` 提供，与 main 里已合入的 3.13 一致；benchdnn 未编入产物。
7. **验证命令**：
   `conan create archives/o/onednn/3.12.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
