# soplex 7.1.6 适配笔记

## 上游信息

- 三方库名称：soplex（SoPlex，Sequential object-oriented Simplex，线性规划求解器）
- 上游版本：7.1.6（对应上游 tag `release-716`，SCIP Optimization Suite 9.2.4 成员，2025-10 发布）
- 上游仓库地址：https://github.com/scipopt/soplex（ZIB 官方只读镜像；原始仓 git.zib.de）
- 主页：https://soplex.zib.de/
- 许可证：Apache-2.0（3.1.1 时代为 ZIB Academic License，7.x 已变更；以 tag 内 LICENSE 文件为准）
- 语言/构建系统：C++14、CMake（`cmake_minimum_required(VERSION 3.9)`）
- 适配路径：路径 A（基础适配）——沿用已合入的 soplex/3.1.1 配方结构与验证结论做版本升级

## 源码选择

- conandata.yml 使用上游 GitHub 镜像的 tag 归档
  `https://github.com/scipopt/soplex/archive/refs/tags/release-716.tar.gz`
  （`strip_root=True`，归档根目录 `soplex-release-716`），
  SHA-256：`f031d60e7ad9a575393b04083c2914fb71a9886ba70ae77931c5a46c76b85ae4`（1,223,488 字节，本地实测下载解包验证）。
- 未使用 ZIB 官网 tarball 的原因：`https://soplex.zib.de/download/release/soplex-7.1.6.tgz`
  实测返回 404（.tar.gz 同），且该站点对自动化下载频繁返回 429（3.1.1 笔记已有记载）；
  GitHub release 页也未上传 7.1.6 附件（仅自动生成的 source 归档）。
  tag 归档来自官方仓库的冻结 release tag，字节稳定，且命中 CI 对 github.com
  的镜像 fallback 逻辑（gh-proxy 等），下载可靠性高于直连 ZIB。

## 与 3.1.1 配方的差异（均经源码核对）

| # | 差异 | 处理 |
|---|------|------|
| 1 | 上游 `cmake_minimum_required` 由 3.0.0 升至 3.9 | 删除 3.1.1 的 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 注入（knowledge E103/E187/E447 仅适用于声明 <3.5 的老版本） |
| 2 | C++ 标准由 C++11 升至 C++14（顶层 CMakeLists 显式设置） | test_package 改用 `cxx_std_14` |
| 3 | 新增可选增强 `BOOST`（默认 ON）、`MPFR`（默认 ON）、`PAPILO`（默认 ON，需 PaPILO≥2.0.0）、`QUADMATH`（默认 OFF）；`SANITIZE_UNDEFINED` 默认由 OFF 变为 ON | 全部显式 OFF：保持与已验证的 3.1.1 一致的 gmp+zlib 最小依赖闭包；`PAPILO=OFF` 另有同系列 scip/10.0.3 已合入先例。`src/CMakeLists.txt` 中 `soplex` 二进制始终构建（`target_link_libraries(soplex libsoplex ${Boost_LIBRARIES})`，BOOST=OFF 时 Boost 变量为空），关闭后 CLI 产物不受影响；ctest settings 固定为 9 组基础项，数量确定 |
| 4 | 许可证变更为 Apache-2.0 | conanfile `license = "Apache-2.0"` |
| 5 | 上游测试规模变化（见下） | MANIFEST 重写审计，`assertion_count: 351` |

## 上游测试清点（审计结论见 test_package/MANIFEST.yml）

- 注册位置：`check/CMakeLists.txt` 的 `add_instancetests` 宏，经 `add_test` 注册为 ctest 用例。
- 实例：`successInstances` 37 个 MPS（27 有限最优值 + 9 不可行 `+infinity` + 1 无界 `-infinity`）；
  `lpInstances` 2 个 LP（afiro、scagr25）；`failInstances` 未定义，贡献 0。
- settings：9 组基础项（default、default-col、default-row、devex、internalsimplifier、
  papilosimplifier、polish1、polish2、steep）。BOOST/MPFR 相关追加项因配方显式关闭而不出现。
- 总数：(37+2)×9 = **351** 个 ctest 用例；判定正则为 `Validation : Success`。
- `tests/c_interface/soplex_c_testing` 为 C 接口冒烟程序（链接 `libsoplexshared`），不在 ctest 注册数内。
- 反证预案（待真机执行时核对）：① `ctest -N` 输出用例数应为 351；② 抽查参照解文件
  `check/instances/*.mps` 非空；③ 如全绿，需确认非空跑——可将 `bin/soplex` 替换为
  `exit 1` 桩后重跑单个用例，确认 harness 报 FAIL（3.1.1 未做此项，7.1.6 预检时补做）。

## 依赖（W0）

- `gmp/6.3.0`、`zlib/1.3.1`：与 3.1.1 完全相同的依赖闭包，仓库内均有归档目录，
  且 3.1.1 已凭此闭包通过验证（built），制品仓已发布；真机预检将以
  `conan download --only-recipe` 复核（R35，不用 `conan list` 判断）。

## 配方要点（conanfile.py generate()）

- OHOS 平台缓存变量 `CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`（与 3.1.1 及同源 scip 配方一致）。
- `GMP=ON`、`ZLIB=ON`（保留有理数求解与 gz 读取能力）；`SANITIZE_UNDEFINED=OFF`；
  `BOOST/MPFR/PAPILO/QUADMATH=OFF`（理由见上表第 3 项）。
- 无补丁（`patches: {}`）。无需 OHOS 源码补丁；平台适配通过 CMake 缓存变量解决。

## test_package（R34 实质调用）

- `test_soplex.cpp`：公开 C++ API（`SoPlex::setIntParam/addColReal/addRowReal/optimize/objValueReal`）
  构建并求解 `min 2*x0+3*x1 s.t. x0+5*x1>=100, x0>=15, x1>=20`，校验最优目标值 90
  （LP 语义复用 3.1.1 已验证用例；`src/example.cpp` 在 7.1.6 源码树中依然存在，API 未变）。
- `test_ohos_soplex.cpp`：鸿蒙专项——编译期 `__aarch64__`/`__linux__` + 运行时
  `/proc/self/exe` ELF `e_machine==183` + 同上公开 API 求解校验。
- `test()` 设 `test_type = "explicit"`，`can_run` 守卫后经 `CONFIG_SHELL` bash 实际执行两个二进制。

## 验证结果（待真机预检回填）

- `conan create`（ohos-aarch64 双 profile）：待 HMBS 真机预检执行。
- 上游 ctest 全量：conanfile `build()` 已接入 `ctest --output-on-failure -j1`
  （可写 TMPDIR，仅替换临时根目录），输出 `HMBS_UPSTREAM_TEST_RESULT` 机器标记并
  持久化到包内 `res/hmbs_upstream.json`（test_package 缓存命中轮复发）；
  待真机执行，预期 351 个用例。
- test_package 消费者 2 用例：待真机执行（`test_soplex: PASS`、
  `test_ohos_soplex: ALL PASS`），输出 `HMBS_TEST_PACKAGE_RESULT` 标记
 （discovered=2/passedCount 实计）。
- 本轮仅完成未提交工作树；以上数字在 evidence 回填前不写入 PR 正文通过率栏。

## 本轮修复（2026-09-18 真机 compile 失败）

- 失败证据：预检解析到 conancenter `gmp/6.3.0`，其 `m4/1.4.19` 的 configure
  报 `/data/service/hnp/bin/bash: inaccessible or not found`（退出码 127），
  伴随 `can't create temporary file /tmp/...: Read-only file system`
 （HMBS readonly_tmp 诊断）。
- 根因：conancenter 版 gmp 带 m4 tool_require，在真机沙箱不可用；
  本仓 `gmp/6.3.0.1`（与 6.3.0 同一上游 tarball，sha256 一致）无 m4 依赖，
  且多带 `--enable-cxx` 的 libgmpxx（SoPlex 有理数 C++ 接口所需）。
- 改动：`requires("gmp/6.3.0")` -> `requires("gmp/6.3.0.1")`；
  test_package shell 按 CONFIG_SHELL->SHELL->/bin/sh 回退（不再硬编码单一路经）；
  主包 `build()` 接入上游 ctest 全量并输出机器标记。

## 本轮修复（2026-09-18 真机 compile 失败第 2 次：zlib）

- 失败证据：gmp/6.3.0.1 已不再报错（m4 链切断生效），改为 `zlib/1.3.1` 在
  `cmake.configure()` 失败：`System is unknown to cmake, create:
  Platform/HarmonyOS` + `The CMAKE_C_COMPILER: /data/service/hnp/bin/clang`
  后配置中断；仍伴随 readonly_tmp 诊断。
- 根因：裸 `zlib/1.3.1` 被解析到 conancenter 的 CMake 配方，其 toolchain 置
  `CMAKE_SYSTEM_NAME=HarmonyOS`（真机 cmake 4.4.3 无该平台模块）且编译器自检
  写只读 /tmp；本仓 `zlib/1.3.1.1` 是同一上游源码的 Makefile 适配配方
 （仅多 CFLAGS=-fPIC），已首发到制品仓并被 curl/python/cups 等消费。
- 改动：`requires("zlib/1.3.1")` -> `requires("zlib/1.3.1.1")`；
  主包 `build()/package()` 与 test_package `build()/test()` 入口新增可写
  tmpdir 保障（按 TMPDIR/TMP/TEMP->$HOME/tmp->build_folder/hmbs-tmp 建目录加
  写探针，命中后导出 TMPDIR/TMP/TEMP/GOTMPDIR；libsedml 先例改编），使本包
  自身 cmake 自检也不写只读 /tmp。

## 本轮修复（2026-09-18 真机 compile 失败第 3 次：编译器死路径）

- 失败证据：zlib 链已通（本轮日志无 zlib 报错），soplex 自身 `cmake.configure()`
  失败：`The CXX compiler identification is unknown` +
  `The CMAKE_CXX_COMPILER: /data/service/hnp/bin/clang++`，定位 build() 第 83 行。
- 根因：真机工具链迁移后 clang/clang++ 已位于
  `/storage/Users/currentUser/usr/local/bin`，`/data/service/hnp/bin` 下无编译器；
  而 profile 的 `tools.build:compiler_executables` 仍钉死旧路径，toolchain 把
  死路径写入 conan_toolchain.cmake（lz4 草稿与 ayatana-indicator-keyboard
  配方注释同款实证）。
- 改动：主包与 test_package 的 `generate()` 新增编译器回退——conf 路径存在则
  沿用（CI worker 不受影响），缺失时经 `shutil.which` 取 PATH 中的
  clang/clang++ 并写入 `tc.variables["CMAKE_C_COMPILER"/"CMAKE_CXX_COMPILER"]`
 （R33：经 Toolchain 落盘，不用裸 shell 变量）；test_package 改为显式
  generate（CMakeDeps 自动 + CMakeToolchain 手动），避免双 toolchain 冲突。

## 交付物

- 静态库 `libsoplex.a` / `libsoplex-pic.a`（另构建 `libsoplexshared.so` 供 `tests/c_interface` 冒烟用，随 `cmake --install` 一并交付）
- `bin/soplex`（CLI LP 求解器，声明见软件级 `archives/s/soplex/commands.json` 的 7.1.6 条目）
- 头文件 `include/soplex.h` 等

## 参考

- 本仓库 `archives/s/soplex/3.1.1/` 全套文件与 notes（含 320/320 ctest 通过记录）
- 本仓库 `archives/s/scip/10.0.3/conanfile.py`（同系列，`PAPILO=OFF` 先例）
- knowledge E103/E187/E447（CMAKE_POLICY_VERSION_MINIMUM 适用边界）
- `.gitcode/code-style.md`、`.gitcode/review-memory.md`（R34/R37/R38/R39 合规自查依据）

---

**编写**: 2026-09-18（首轮工作树，待真机预检）
**最终状态**: 未验证（unverified）
