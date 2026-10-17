# serialize 1.4.4 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE library，上游自带 CTest 测试入口）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4（OHOS aarch64，`--target=aarch64-linux-ohos`，OHOS SDK sysroot）
- 状态: built（本地 conan create 通过 + test_package 2/2；未 upload）

## 库与目标确认
- 目标库: **serialize**（Glenn Fiedler / Más Bandwidth LLC）—— 单头文件 C++ 位打包序列化库（`serialize.h`）。
- 上游仓库: https://github.com/mas-bandwidth/serialize
- 上游 tag: `refs/tags/v1.4.4` → commit `3a066b8bc8798b6b6dfbfecfd348ad63f82c3bd4`
- 源码 tarball: https://github.com/mas-bandwidth/serialize/archive/refs/tags/v1.4.4.tar.gz
- SHA-256: `635c7d0b04bdee3256ca7ac5fc91ae5dea14f08368496dd6cc28f7bd49905e70`（实测，写入 conandata.yml）
- 命名口径: 任务给出的库名 `serializeC++` 即 C++ 版 serialize（该库本身只有 C++ 实现）；Conan 包名取上游工程名 `serialize`，与上游 CMake `project(serialize ...)` / `find_package(serialize)` 一致。

## 依赖与查重
- 依赖: **无**（header-only，仅 C++ 标准库；`serialize::serialize` 为 INTERFACE target，无链接产物）。W0 依赖预检无需外部包。
- 查重: `git ls-remote --heads origin|upstream` 无 `serialize` 分支；`find archives -ipath '*serialize*'` 仅命中 `archives/s/serializer`（不同库，eyalz800/serializer）与 `archives/b/bitserializer`（不同库）；制品仓 `conan list "*serialize*" -r=ohpcd` 仅 `bitserializer/0.85.0`。无同库同版本记录，非重复适配。

## 编译步骤
```bash
# 本地原生验证（W3 同源路径）
conan create archives/s/serialize/1.4.4 -pr:h=default -pr:b=default --build=missing
#   → conanfile build() 内 cmake.test()：上游 CTest 1/1 通过
#   → test_package：test_serialize 与 test_serialize_ohos 2/2 通过

# OHOS aarch64 交叉编译 + 实机运行（本机 OHOS SDK clang 15）
clang++ --target=aarch64-linux-ohos --sysroot=<ohos-sdk>/native/native/sysroot \
        -std=c++11 -O2 -DNDEBUG -I<src> test_package/ohos_serialize_test.cpp -o test_serialize_ohos
./test_serialize_ohos
#   → PASS: HarmonyOS platform checks passed (LE=1, sizeof(wchar_t)=4, 1.4.4)
```

## 上游测试（R51 三步法）

**计数口径（全仓统一，本任务唯一口径）：以「上游测试函数数」计，即 `serialize.h` 内
`#if SERIALIZE_ENABLE_TESTS` 块中 `SERIALIZE_RUN_TEST(...)` 注册的测试函数，共 17 项。**
CTest 侧 `add_test(NAME test COMMAND serialize_test)` 只注册 1 个 case，该 case 顺序执行全部
17 个测试函数；两种口径并存，本任务统一采用「测试函数数 = 17」。

1. **清点**：`grep -o 'SERIALIZE_RUN_TEST( *test_[a-z0-9_]*' serialize.h | wc -l` → 17；
   断言粒度 `grep -c 'serialize_check(' serialize.h` → 175 项。
2. **实跑（真机/OHOS 运行时）**：OHOS aarch64 工具链编译 `test.cpp`（`-DSERIALIZE_ENABLE_TESTS=1`）
   后在 OHOS/musl aarch64 运行时执行 → `*** ALL TESTS PASS ***`（17/17 测试函数，0 失败）。
   本地原生（macOS arm64）同一入口 `ctest` 1/1 通过，两平台结果一致。
3. **回填**：本文件与 MANIFEST.yml / PR 正文均按 17 项口径填写（详见「验证结果」）。

## 测试计数口径
| 口径 | 数值 | 证据 |
|------|------|------|
| 上游测试函数数（`SERIALIZE_RUN_TEST`） | 17 | `grep -o 'SERIALIZE_RUN_TEST( *test_[a-z0-9_]*' serialize.h \| wc -l` |
| 上游 CTest 注册 case 数 | 1 | `add_test(NAME test COMMAND serialize_test)`（顺序跑 17 个函数） |
| 上游 `serialize_check` 断言数 | 175 | `grep -c 'serialize_check(' serialize.h` |
| test_package 消费者用例 | 1 | `test_serialize.cpp`（25 项 CHECK） |
| 鸿蒙特有测试 | 1 | `ohos_serialize_test.cpp`（22 项 CHECK） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CMake 把测试/示例/基准三个可执行目标都挂在 `SERIALIZE_BUILD_TESTS` 下 | `option(SERIALIZE_BUILD_TESTS ...)` 是单一开关，没有"只开测试"的独立选项 | 保留该开关（不裁剪上游目标），仅通过 `SERIALIZE_FUZZ=OFF` 关闭需要 libFuzzer 的 fuzz 目标；示例/基准与测试同源编译，对 W3 无副作用 |
| 2 | `cmake.test()` 在跨编译（OHOS profile）时执行失败：`bin/test ... [exec format error]` | 交叉编译产物是 aarch64-linux-ohos ELF，无法在构建机（macOS）直接执行——属构建机限制，不是代码缺陷 | 上游测试通过**目标平台真实运行**验证（OHOS aarch64 musl 运行时实跑 17/17；本机原生跑同源 1/1）；`test_package` 按本仓惯例用 `cross_building()` 跳过跨编译运行 |
| 3 | `test_package/conanfile.py` 同时声明 `generators = (... 'CMakeToolchain')` 又在 `generate()` 里 `CMakeToolchain(self)` | Conan 2 禁止同一 generator 双重声明 | 从 `generators` 移除 `CMakeToolchain`（保留 `CMakeDeps` + `VirtualRunEnv`），`generate()` 内显式实例化以便注入 OHOS 目标三元组 |
| 4 | 头文件字节序回退链不含 `__aarch64__`/`__arm__` | `serialize.h` 的架构宏兜底只列 x86/ppc/ia64 等（ARM 侧仅 `_M_ARM64`，即 MSVC-on-Windows-ARM64），aarch64 依赖首选分支 `__BYTE_ORDER__` | OHOS clang 15 **定义了** `__BYTE_ORDER__`，首选分支命中，无需补丁；已实测确认（见「OHOS 平台验证」）。仅在编译器不提供 `__BYTE_ORDER__` 时才需要 `-DSERIALIZE_LITTLE_ENDIAN`，此为上游既定契约（头文件 `#error` 已明示） |

## 源码修改
- **无 patches/**。上游在 OHOS 上零修改即可编译、通过全部测试；本地优先顺序依次核验了
  「构建参数/toolchain → 上游平台抽象（`__BYTE_ORDER__`/`SERIALIZE_LITTLE_ENDIAN`/`SERIALIZE_BIG_ENDIAN` 三个覆盖宏）
  → 最小源码补丁」，第 1、2 层已覆盖，未触发第 3 层。

## OHOS 平台验证（鸿蒙特有测试）
`test_package/ohos_serialize_test.cpp`，在 OHOS aarch64 musl 运行时实跑通过（22 项 CHECK），覆盖三类
由平台/ABI 决定、而非库逻辑决定的行为：

1. **字节序检测与实机布局一致**：`SERIALIZE_LITTLE_ENDIAN==1`、`SERIALIZE_BIG_ENDIAN==0`，且对
   `0x11223344` 的内存探测为 `44 33 22 11`（LSB 在前），证明宏协商结果与目标真实字节序一致。
2. **小端 wire format**：库定义 network byte order 为小端，OHOS aarch64 上 `host_to_network()` /
   `network_to_host()` 均为恒等映射；`SerializeBits(0xDEADBEEF,32)` 落盘字节为 `EF BE AD DE`。
3. **OHOS wchar_t 为 4 字节**：`sizeof(wchar_t)==4` 使 `serialize_wstring_internal` 走 4 字节分支，
   非 BMP 码点 `U+1F600` 与 BMP 边界 `0xFFFF` 完整往返；线上格式固定 32 bit/字符（长度前缀 + 每字符
   32 位），因此与 2 字节平台保持字节级兼容（2 字节平台读取 >BMP 码点返回 false 而非截断）。

```bash
# 实测输出（OHOS aarch64 musl 运行时）
aarch64
test_serialize: consumer API verification passed (1.4.4)
consumer RC=0
test_serialize_ohos: HarmonyOS platform checks passed (LE=1, sizeof(wchar_t)=4, 1.4.4)
ohos RC=0
```

## 验证结果
```bash
# 上游测试（OHOS aarch64 实跑，17 个测试函数）
./bin/test → 17/17 测试函数通过，*** ALL TESTS PASS ***（0 失败）

# 上游测试（本机原生 CTest，1 个 case 顺序跑 17 个函数）
100% tests passed, 0 tests failed out of 1

# conan create（原生 profile）
conan create archives/s/serialize/1.4.4 -pr:h=default -pr:b=default --build=missing
→ serialize/1.4.4 package created
→ test_package: 2/2 通过（test_serialize, test_serialize_ohos）
```

## 交付物
| 文件 | 说明 |
|------|------|
| `conanfile.py` | header-only CMake 配方：保留上游 `cmake.test()`（层 1）、`CMake.install()` 安装上游布局、`cpp_info` 暴露 `serialize::serialize` |
| `conandata.yml` | 官方 tag v1.4.4 URL + 实测 SHA-256 |
| `manifest.yaml`（版本级/软件级） | 编译元数据与跨版本 OHOS 适配知识 |
| `test_package/` | 消费者测试 `test_serialize.cpp` + 鸿蒙专项测试 `ohos_serialize_test.cpp` + `MANIFEST.yml` |
| `notes.md` | 本文件 |

## 知识查重判定（本地只读快照，knowledge @ main HEAD=48d9cee684）
- 扫描范围: `knowledge/graph/E*.kv`（540 条）+ `knowledge/doc/E*.md` + `knowledge/drafts/*.kv`
- 最相关既有知识:
  - **E321**（martinmoene/nonstd-lite 系 header-only Conan 2.x 迁移）：命中"header-only + CMake INTERFACE +
    `package_type=header-library` + `cmake_file_name`/`cmake_target_name`"配方骨架。本配方沿用该骨架
    （`cmake_layout`、`export_conandata_patches`、`cpp_info.set_property`），但 serialize 与 nonstd-lite 系不同：
    它有**真实上游 CTest 入口**（nonstd-lite 用 `*_OPT_BUILD_TESTS` 变体编译），因此 `build()` 走
    `CMake.configure/build/test` 而非无构建。
  - **E257**（header-only 无构建系统库的 no-op `build()` G1 门禁）：适用于"无 CMake 工程"的单头文件库；
    serialize 上游自带 CMake 工程，不适用该 no-op 分支。
- 无 serialize 专属正式条目或草稿（formal/drafts 全量检索为空）。
- **knowledge_decision: reuse_existing（路径 A）**，不创建新草稿。
  第 4 项"字节序回退链不含 `__aarch64__`"经核验**不构成平台阻塞**（OHOS clang 定义了 `__BYTE_ORDER__`），
  属上游既定契约而非鸿蒙知识缺口，故不作路径 B 候选。

---

**编译结束**: 2026-09-22
**最终状态**: built
