# libcombine 0.2.20 适配笔记

## 基本信息

- 上游：https://github.com/sbmlteam/libCombine（tag v0.2.20，BSD-2-Clause）
- 主页：https://sbml.org/software/libcombine/
- 构建系统：CMake（C++11），`src/` + 顶层 `CMakeLists.txt`
- 适配路径：路径 A（基础适配）
- 分支：`feat/libcombine-0.2.20`，基于 `upstream/main@9f5ee6b`
- 状态：首轮工作树（未提交），待 HMBS 真机预检

## 源码与校验

| 源码 | URL | sha256 |
|------|-----|--------|
| libCombine v0.2.20 | `https://github.com/sbmlteam/libCombine/archive/refs/tags/v0.2.20.tar.gz` | `2b4f76d4…3c1`（1525273 B，已下载实测，与 FreeBSD distinfo 一致） |
| zipper@c56a27f | `https://github.com/fbergmann/zipper/archive/c56a27f….tar.gz` | `7705accb…9459a`（已下载实测） |
| minizip@e3a8cb7 | `https://github.com/sebastiandev/minizip/archive/e3a8cb7….tar.gz` | `6a663283…aa5188`（已下载实测） |
| libSBML v5.20.5 | `https://github.com/sbmlteam/libsbml/archive/refs/tags/v5.20.5.tar.gz` | `21c88c75…6e7e0a`（28852940 B，已下载实测） |

## 依赖分析（W0）

- 制品仓已发布：`zlib/1.3.1`（静态，R26）、`libxml2/2.15.3`（共享）——配方 `requirements()` 引用。
- 未发布：`libsbml`（制品仓与 `archives/` 均无）。libCombine 全系头文件包含
  `<sbml/xml/*>`、`<sbml/util/*>`，`FindLIBSBML.cmake` 为 REQUIRED，不可裁剪。
- 单 PR 约束下采取 vendor 方案：libSBML 5.20.5（与 0.2.20 同时期稳定版）源码随包，
  在 `build()` 内先编出私有静态库（core only：`WITH_LIBXML=ON/WITH_ZLIB=ON`，
  关闭 bzip2/swig/packages/examples/check），头文件与 `libsbml-static.a` 随包发布。
  后续应拆分为独立 `libsbml` 配方（见补充说明），本包届时改为常规 `requires`。
- zipper/minizip：复用 FreeBSD `biology/libcombine` 的 GH_TUPLE 做法，
  解包到 `submodules/zipper`、`submodules/zipper/minizip`，与上游
  `if (EXISTS submodules/zipper)` 内嵌逻辑对接。

## 上游测试清点（R51 三步法第 1 步）

- 位置：`src/test/`，Catch 单头（`catch.hpp`）+ `main.cpp`。
- 测试源 5 个：`combine_test_create.cpp`（4 SCENARIO + 2 TEST_CASE）、
  `zip_test_read.cpp`（1 SCENARIO）、`zip_test_write.cpp`（1 SCENARIO）、
  `util_test.cpp`（1 SCENARIO）、`metadata_test_create.cpp`（1 SCENARIO），
  合计 **10 个 Catch 用例**，经 1 个 ctest 项 `test_Combine_run` 运行。
- 另有 `tests/test_combine.py`（SWIG 绑定测试，本次不启用绑定，不计入）。
- 配方 `BUILD_TEST=ON`，`build()` 末尾 `can_run` 时执行 `cmake.test()`（即
  `ctest --output-on-failure`）；测试用 `srcdir` 由 ctest 属性注入。
- 注意 FreeBSD 曾因 0.2.19 zipper 相对路径 bug（issue #58）禁用测试；
  0.2.20 已合入 #53/#54 路径修复与 #59 零长文件修复，本配方保持测试开启，
  若真机复现链接问题再回退并如实申报。

## 编译步骤（真机将执行）

```bash
conan create archives/l/libcombine/0.2.20 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

流程：vendor libSBML（`sbml-build`→`sbml-prefix`，`--parallel 1`）→
`CMAKE_PROJECT_INCLUDE` 注入 `LIBSBML_*`/`EXTRA_LIBS` → 主工程 configure/build →
ctest → install（含 vendor 头/库 + LICENSE）→ test_package 往复测试。

关键兼容点：

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake_minimum_required(VERSION 2.6...3.19)` 在 CMake ≥4 报错 | 上游下限过旧 | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（toolchain + 两处 configure） |
| 2 | `find_package(LIBSBML REQUIRED)` 无处可找 | 制品仓无 libsbml | vendor 源码 + 缓存变量直传 `LIBSBML_LIBRARY/INCLUDE_DIR` |
| 3 | `EXTRA_LIBS` 裸写 `xml2` 链不上 conan 包 | 无 `-L` 路径 | 传完整 `.so`/`.a` 路径 + 系统 `m` |
| 4 | `.so` 在 HarmonyOS 设备上拒绝加载（参考 libxml2 经验） | 缺 `.codesign` | `package()` 内 guarded 重签名（工具不存在则跳过） |
| 5 | 上游 `WITH_SWIG=ON` 默认找 swig | 设备无 swig | `-DWITH_SWIG=OFF`（绑定本次不做） |

## test_package（R34）

`test_combine.cpp` 实调 API：`KnownFormats::isFormat/lookupFormat`、
`Util::getExtension/getDefaultTempDir`、`CombineArchive::addFileFromString`、
`addMetadata/hasMetadata`、`writeToFile/initializeFromArchive`、
`extractEntryToString/getMetadataForLocation/cleanUp`、
`OmexDescription/VCard` 建模与回读校验，共 19 个 PASS/FAIL 检查点，
失败返回非零。`MANIFEST.yml` 声明上游 5 文件与 L1 用例。

## 验证结果

- 本机：仅完成源码下载 + sha256 实测 + 配方静态走读，未跑 conan（按任务守则，
  编译验证统一走 HMBS 真机）。
- 真机预检：待 HMBS 后台执行；`HMBS_TEST_PACKAGE_RESULT` /
  `HMBS_UPSTREAM_TEST_RESULT` 标记与通过率以预检日志为准回填。

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/l/libcombine/0.2.20/conanfile.py` | 主配方（CMake + vendor sbml/zipper/minizip） |
| `archives/l/libcombine/0.2.20/conandata.yml` | 4 处官方源 URL + sha256 |
| `archives/l/libcombine/0.2.20/manifest.yaml` | 版本 manifest |
| `archives/l/libcombine/0.2.20/test_package/` | `conanfile.py`、`CMakeLists.txt`、`test_combine.cpp`、`MANIFEST.yml` |
| `archives/l/libcombine/0.2.20/notes.md` | 本文件 |
| `.hmbs/pr-body.md` | PR 正文草稿（测试数字待真机回填） |

## 注意事项

- 本轮严禁 commit/push/建 PR；工作树保持未提交，待真机全部门禁通过后由 HMBS 统一提交。

## 第 2 策略周期：CMake 自带 OHOS 平台名（2026-09-16 第二次修复）

- 上上轮改走 NDK 自发现 + 裸 cmake，首跑即报 `Invalid configuration:
  Cannot find ohos.toolchain.cmake`：预检 worker 上根本没有该 NDK 文件
  （CI profile 亦不设 user_toolchain/OHOS_NDK_HOME），硬依赖 NDK 即硬失败
  ——证伪"NDK 必存在"假设（nanoarrow 0.9.0 第 10→11 轮同型教训）。
- 本轮换混合路线（yaml-cpp 0.9.0 / nanoarrow 0.9.0 已验证）：
  `tc.blocks["generic_system"]` 置 `cmake_system_name="OHOS"` +
  `cmake_system_processor="aarch64"`；CMake 4.x 自带 `Platform/OHOS.cmake`
  （即 Linux 平台逻辑），无需 NDK 文件，profile clang 直驱；vendored
  libSBML 与主工程均以生成的 conan_toolchain 配置；TMPDIR 经 buildenv
  脚本持久化（readonly_tmp 双保险）；test_package 保持直接 cxx 编译。

## 同指纹第 3 次修复：可运行编译器发现与落盘证据（2026-09-16）

- 前次 generic_system OHOS 已消除 `Platform/HarmonyOS` 报错，新失败为
  `The C/CXX compiler identification is unknown`（仍止于 vendored SBML
  configure）：conan_toolchain 写入的 profile 绝对路径
  `/data/service/hnp/bin/clang(++)` 在预检 worker 上可能根本跑不起来
  （nanoarrow 0.9.0 实证：Errno 2 on --version），且摘要截断隐藏真实 stderr。
- 本轮策略（与前两次不同）：`generate()` 新增 `_discover_compilers()`，
  候选（profile→PATH→知名绝对目录）逐个 `--version` 实跑验证后才 pin
  `CMAKE_C/CXX_COMPILER`；buildenv 追加 SDK llvm/lib 的
  `LD_LIBRARY_PATH`（lld 需 libxml2.so.16）；两处 configure 包
  try/except，失败时落盘 `CMakeError.log`/`CMakeOutput.log` 尾部；
  test_package `_cxx` 同步加 `--version` 可运行校验。

- 上一周期三连败复盘：三轮都在 conan_toolchain 上修修补补（cache_variables 设
  Linux → 生成后文件重写 HarmonyOS→Linux），但预检仍止于
  `_build_vendored_sbml()->self.run(configure)`，`System is unknown to cmake,
  Platform/HarmonyOS` + `CMAKE_C/CXX_COMPILER=/data/service/hnp/bin/clang`
  compiler check 失败。根因：SYSTEM_NAME=Linux 与 OHOS 编译器标志
  （aarch64-linux-ohos target/sysroot）自相矛盾，compiler test 必然失败；
  且 OHOS 适配版 Conan 模板在用户值之后仍写入 HarmonyOS，覆盖/重写均不可靠。
- 新路线（与 libxml2/2.15.3.1、libxslt/1.1.45.1、zstd/1.5.6 同法，ML-0035）：
  删除 `generate()`/conan_toolchain，主工程与 vendored libSBML 均用
  `_ohos_toolchain()` 自发现 `ohos.toolchain.cmake` + 裸 cmake
  （`-DCMAKE_TOOLCHAIN_FILE + -DOHOS_ARCH=arm64-v8a`），工具链内外一致。
- test_package 同步改为直接 cxx 编译+运行（libxml2/2.15.3.1 前例），不再经
  CMake consumer configure，顺带补 `HMBS_TEST_PACKAGE_RESULT` 实计数标记；
  主工程 ctest 后解析 Catch 汇总并输出 `HMBS_UPSTREAM_TEST_RESULT`。
- 若预检报 `unpublished_deps`（zlib/libxml2 侧），按 W0 停留上报，不加 workaround。
- 若 vendor sbml 构建超时（jobs=1 下约数分钟），按 `ci/config/build_timeouts.txt` 机制补预算。
- 后续拆分 libsbml 独立配方后，本配方删除 vendor 段并改回 `requires("libsbml/...")`。
