# libjxl-tools 0.11.2 路径 B 困难库适配分析报告

- **上游仓库**：https://github.com/libjxl/libjxl （v0.11.2）
- **适配包**：`libjxl-tools/0.11.2`（命令行工具 `cjxl` / `djxl` / `jxlinfo`）
- **平台**：HarmonyOS PC（OHOS / aarch64，clang 15，Conan 2.29.1）
- **PR**：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/12667

---

## 1. 申报边界

- **申报**：路径 B（贡献创新）—— 以「困难链根因 + 可复用知识条目」为申报材料，不依赖仅对本软件生效的单点补丁。
- **不申报**：路径 C（高难度挑战）。本包无私有工具链、无汇编/SIMD 手写、无超大依赖或系统级缺口证据，不具备路径 C 材料。
- **不重复计分**：本报告的诊断结论与随附知识草稿（第 4 节）为本任务唯一贡献申报口径；依赖（brotli/highway/libpng/zlib）均为普通适配事实，不单独申报依赖附加分。
- **材料性质**：第 3 节的失败链与第 6 节的验证证据均可由第三方按命令复核；第 7 节如实列出未解决项。

## 2. 软件与适配对象

`libjxl-tools` 由 libjxl 源码树构建用户态命令行工具（`cjxl` 编码 / `djxl` 解码 / `jxlinfo`
容器信息）。上游构建系统为 CMake，依赖 highway（SIMD 抽象）与 brotli（熵编码）。

与「纯库适配」的关键差异：**工具链包必须自包含**（`bin/` 下的可执行文件在用户机器上
直接运行），因此所有动态依赖必须在包内可解析，而不能像库那样依赖消费方注入运行环境。

## 3. 真实失败链

### 3.1 `JPEGXL_STATIC=ON` → lld 拒绝静态链接动态对象

```text
ld.lld: error: attempted static link of dynamic object '.../libbrotlienc.so'
```

`JPEGXL_STATIC=ON` 向 `EXE_LINKER_FLAGS` 追加 `-static`，强制整个可执行文件（含所有传递依赖）
静态链接；而制品仓的 `brotli/1.2.0` 仅产出共享 `.so`，lld 因此拒绝链接。**该选项语义（全静态
可执行）与「外部依赖以共享形式提供」的制品仓现实结构性冲突**，不是参数调优问题。

### 3.2 隐式必需依赖（PNG/APNG）偶合宿主前缀 → 包不自包含（本任务质检打回的缺陷）

`conan create` 成功、`test_package`（当时仅 `--version` + `conanrun` 环境）亦"通过"，
但产物在**干净环境**下不可运行：

```text
$ env -i <pkg>/bin/cjxl --version
Error loading shared library libpng16.so.16: (needed by <pkg>/bin/cjxl)
Error relocating <pkg>/bin/cjxl: png_destroy_read_struct: symbol not found
```

根因链：libjxl 的 extras 编解码器**无条件**执行 `find_package(PNG)`（APNG 编解码无条件编译）；
CMake 官方 `FindPNG` 先 `find_package(ZLIB)` 再读 `PNG_PNG_INCLUDE_DIR` / `PNG_LIBRARY`，
这些变量被构建机**宿主前缀**满足（构建日志 `-- Found PNG: /storage/.../usr/local/lib/libpng16.so
(found version "1.6.43")`）→ 二进制得到 `DT_NEEDED libpng16.so.16`，而包内 `lib/` 未随附 →
仅当宿主 `LD_LIBRARY_PATH` 存在时才"可用"。**这是"编译通过 + 横幅测试通过"无法发现的假阳性。**

### 3.3 已发布共享库的 DT_NEEDED 为无 SONAME 的 `libz.so`，而仓内 zlib 纯静态

```text
$ readelf -d <pkg>/lib/libpng16.so.16 | grep NEEDED
  (NEEDED)  Shared library: [libz.so]     # 无版本号（非 SONAME 形式）

$ ls /usr/lib/libz*
/usr/lib/libz.so.1  /usr/lib/libz.so.1.2.13   # 系统不提供名为 libz.so 的文件
```

制品仓 `zlib/1.3.1.1` 仅产出静态 `libz.a`；已发布的 `libpng/1.6.58` 的共享库把 `libz.so`
（不含版本）写入 `DT_NEEDED`，导致 `libpng16.so.16` 在干净环境载入失败——**依赖链两端的
产物形态不匹配**，且该不匹配在链接期与常规测试期均不可见。

### 3.4 上游测试数据缺失导致 gtest 二进制中途 SIGTRAP（通过率失真）

```text
[ RUN      ] SplinesTest.Drawing
ReadTestData /storage/.../s/testdata/jxl/splines.pfm
Signal 5 (core dumped)
```

libjxl 测试数据在**独立仓库** `libjxl/testdata`，发布 tarball 不含该子模块；且
`lib/jxl/test_utils.cc` 的 `GetTestDataPath()` 由**编译期宏** `-DTEST_DATA_PATH`
（CMake 变量 `JPEGXL_TEST_DATA_PATH`）固化，**运行时设置 `TEST_DATA_PATH` 环境变量无效**。
数据缺失 → `ReadTestData()` 触发 `JXL_CRASH()` → SIGTRAP → 整个二进制中止、后续用例不再执行。
**后果：通过率被严重低估（8.6% 假象 vs 真实 99.92%）。**

## 4. 可复用的诊断结论

本任务随附 4 条知识草稿（`knowledge/drafts/`），均为**跨组件可复用**的通用模式而非本包特例：

| # | 知识草稿 | 可复用边界 |
|---|----------|-----------|
| 1 | `DRAFT-libjxl-tools-0.11.2-png-required-dependency-pinning` | 任何「官方 CMake Find 模块 + 宿主前缀存在同名库」的项目；给出「显式声明 + 钉扎 cache 变量 + 随包 `.so` + `env={}` 空环境断言」四步模式 |
| 2 | `DRAFT-libjxl-tools-0.11.2-static-zlib-dt-needed-libz-soname` | 依赖「已发布共享库 + 其传递依赖仅静态」的任意包；给出由静态库合成包内共享库（不污染系统 `/lib`）的做法 |
| 3 | `DRAFT-libjxl-tools-0.11.2-jpegxl-static-forces-shared-deps` | 任何提供 EXE 全静态开关、但依赖链含 `.so`-only 配方的 CMake 项目 |
| 4 | `DRAFT-libjxl-tools-0.11.2-upstream-testdata-compile-time-path` | 任何「测试数据为独立子模块、路径由编译期宏固化」的上游项目；含镜像取数方法与通过率口径要求 |

其中 1、3 两条共同刻画了「**制品包自包含性**」这一类缺陷的检测与修复模式（本任务的核心创新点）；
4 条刻画了「**通过率口径**」问题的定位方法。

## 5. 与现有材料的差异

- 现有知识库已有 `E092`（CMake 不识别 HarmonyOS 平台）——本任务沿用该结论（`CMAKE_SYSTEM_NAME=Linux`），**不重复申报**。
- 现有材料未覆盖：① CMake 官方 Find 模块被宿主前缀满足导致的**包不自包含**；② 已发布共享库
  的非 SONAME `DT_NEEDED` 与静态-only 传递依赖的**产物形态不匹配**；③ **编译期宏**形式的
  测试数据路径（区别于运行时环境变量）。
- 第 3 节的失败链均为**本任务独立复现**（质检 `env -i` 复现 3.2；`readelf -d` 复现 3.3；
  `compile_commands.json` 复现 3.4），不是推测。

## 6. 验证证据

```bash
# 编译与门禁
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify libjxl-tools 0.11.2
# → G0/G1/G2/G3 PASS；包 revision fad5b909… → 修复后 5ea0d09f…；包 ID a8c57f366e0313c323f14358e52e86babaec949e

# 依赖钉扎生效（构建日志不再指向宿主前缀）
# -- Found PNG:  .../.conan2/p/libpne65b0a3aa7f9b/p/lib/libpng16.so (found version "1.6.58")

# 包自包含（干净环境，无 LD_LIBRARY_PATH）
env -i <pkg>/bin/cjxl --version    # cjxl v0.11.2 503c4c2c9 [NEON_WITHOUT_AES]  rc=0
env -i <pkg>/bin/djxl --version    # djxl v0.11.2 503c4c2c9 [NEON_WITHOUT_AES]  rc=0
env -i <pkg>/bin/jxlinfo --help    # Usage: ...  rc=0
env -i <pkg>/bin/cjxl in.ppm out.jxl     # rc=0, out.jxl 72 B
env -i <pkg>/bin/djxl out.jxl out.ppm    # rc=0, out.ppm 59 B
env -i <pkg>/bin/jxlinfo out.jxl         # JPEG XL image, 4x4, lossy, 8-bit RGB  rc=0

# 上游测试（62 个 gtest 二进制）
# 定义用例 4782 / 通过 4778（99.92%）/ 断言失败 0 / 未执行 2 / SKIPPED 1 / DISABLED 1
```

| 检查项 | 结果 |
|--------|------|
| `conan create`（aarch64-unknown-linux-ohos, clang 15） | ✅ 通过 |
| G0 / G1 / G2 / G3 | ✅ PASS |
| L2 smoke（`cjxl`/`djxl --version`、`jxlinfo --help`） | ✅ 通过 |
| L4 checksec | ✅ 三工具均 PIE + NX + full RELRO(BIND_NOW) |
| 干净环境自包含（`env -i`） | ✅ 通过（修复前失败，为本任务发现的真实缺陷） |
| 上游测试通过率 | **4778/4782 = 99.92%**，断言失败 0 |
| 新增 test_package 通过率 | 1/1（100%） |

## 7. 测试完整性与未解决项

- **上游测试执行完整性**：62 个测试二进制全部构建成功；4782 个定义用例中 4778 通过。
- **未执行 2 例**：`splines_test`（`SplinesTest.Drawing` 读 `jxl/splines.pfm`）——该文件
  **不存在于上游 `libjxl/testdata@main`**（GitHub API 返回 404；全仓 `.pfm` 仅一个无关文件），
  属上游测试数据缺失，**非本适配缺陷**；补齐数据后即可执行。
- **SKIPPED 1 例 / DISABLED 1 例**：均为上游行为（`gauss_blur_test` / `jxl_test`）。
- **未解决项**：不适用 —— `libz.so` 的合成方案依赖「静态 `libz.a` 以 `-fPIC` 构建」这一前提；
  若上游制品仓日后改为提供共享 zlib，应优先使用共享包而非合成（已在知识条目中记录降级路径）。
- **未修改上游任何测试源码**；仅独立测试构建的两项 CMake 配置调整（`JPEGXL_ENABLE_FUZZERS=OFF`、
  `CMAKE_GTEST_DISCOVER_TESTS_DISCOVERY_MODE=PRE_TEST`），已在 notes.md 记录。

## 8. 评审请求

申请评审委员会按「路径 B：困难库适配分析报告」审阅本材料，重点复核：

1. 第 3.2 节的**包自包含性缺陷模式**（官方 CMake Find 模块被宿主前缀满足）是否达到可复用知识的收录标准；
2. 第 3.3 节「静态-only 传递依赖 + 非 SONAME `DT_NEEDED`」的合成方案是否认可为通用解法（含不污染系统 `/lib` 的边界）；
3. 第 3.4 节**编译期宏路径**与通过率口径（定义 / 已执行 / 通过 / 断言失败四项分列）是否应纳入测试验证规范；
4. 是否认可 `libjxl-tools/0.11.2` 作为路径 B（贡献创新）申报；本任务**不申报路径 C**。

最终分类与分值与知识条目编号以官方审核为准。
