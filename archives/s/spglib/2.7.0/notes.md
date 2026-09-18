# spglib 2.7.0 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-15
- 编译器: clang/clang++ (OHOS aarch64, profile 提供)
- 状态: built (待真机预检确认)
- 上游: https://github.com/spglib/spglib tag v2.7.0
  SHA256=b22fc9abae9716c574fbc6d55cfc53ed654a714fccc5657a26ff5d18114bd8bd
  (Spack 内建记录同值；真机 conan create 实测校验)
- 文档主页: https://spglib.readthedocs.io/
- 许可证: BSD-3-Clause

## 编译步骤

配方 (conanfile.py) 采用 cmake_layout + CMakeToolchain：

```cmake
SPGLIB_SHARED_LIBS=OFF (Conan shared=False 映射；默认静态交付)
SPGLIB_WITH_Fortran=OFF
SPGLIB_WITH_Python=OFF
SPGLIB_USE_OMP=OFF
SPGLIB_WITH_TESTS=ON
SPGLIB_INSTALL=ON
```

流程: `cmake.configure()` -> `cmake.build()` -> 单次
`ctest --output-on-failure` (捕获输出并解析
`"% tests passed, % tests failed out of N"` 汇总行，
输出 `HMBS_UPSTREAM_TEST_RESULT` 机器标记并落盘
`build_folder/hmbs_upstream.json`；`package()` 复制到
`package/res/hmbs_upstream.json` 供 test_package 缓存命中轮次复发) ->
`cmake.install()`。

`package_info()`: `libs=["symspg"]`,
`cmake_file_name=Spglib`, `cmake_target_name=Spglib::symspg`,
`pkg_config_name=spglib`; `os in ("Linux","OHOS")` 时
`system_libs=["m"]` (R32)。

## 上游测试清点 (R51 三步法申报)

- 位置: 上游 `test/` 目录，`test/CMakeLists.txt` 注册 5 类套件：
  `unit` / `integration` / `functional` / `package` / `example`。
- 框架: ctest。`SPGLIB_WITH_TESTS` 默认跟随 `PROJECT_IS_TOP_LEVEL`
  (顶层构建为 ON)；配方显式设为 ON。
- 单元测试实现: `test/unit` 经 FetchContent 拉取
  `googletest v1.15.2`，链接 `GTest::gtest` / `GTest::gtest_main`
  与 `Threads::Threads` (见上游 `test/CMakeLists.txt`)；
  功能/集成/打包/示例测试经 `Spglib_add_test()` 以
  `ctest --build-and-test` 形式驱动。
- Python 覆盖: 上游另有 pytest 覆盖更多用例，但配方关闭
  Python 接口 (`SPGLIB_WITH_Python=OFF`)，C 库口径以 ctest 为准。
- 执行: 真机 `conan create` 中完整运行
  `ctest --output-on-failure`；通过率以预检日志中
  `HMBS_UPSTREAM_TEST_RESULT` 的 discovered/executed/passed
  为准，不估算、不照抄文档。
- 证伪: 按任务守则，退出码 0 不等于真跑——核对 ctest 汇总行
  非零、参照数据非空；Python 绑定等未运行部分在 PR
  补充说明中如实声明，不计入通过。

## 消费者测试 (test_package)

`test_package/test.c` 以库使用者身份调用公开 C API：构造单原子
简立方晶胞 (lattice=单位矩阵，position=(0,0,0))，调用
`spg_get_dataset`，断言返回非空、`spacegroup_number==221` (Pm-3m)、
`n_operations>0`、`international_symbol` 非空，并 `spg_free_dataset`
释放；另校验 `spg_get_version` / `spg_get_version_full` 非空。
共 7 条 CHECK-OK 断言，失败退出码非零。

`test_package/conanfile.py` 用 CMake 构建并经 `ctest` +
二进制直跑双重执行，统计 `CHECK-OK:` 行数产生
`HMBS_TEST_PACKAGE_RESULT` (discovered=7)；同时从
`package/res/hmbs_upstream.json` 复发实测的
`HMBS_UPSTREAM_TEST_RESULT` (缓存命中轮次仍有证据)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游单元测试需 FetchContent 拉取 googletest | `test/CMakeLists.txt` 写死 `GIT_REPOSITORY https://github.com/google/googletest, GIT_TAG v1.15.2` | 保持 `SPGLIB_WITH_TESTS=ON` 让真机实测；若预检报网络/获取失败，下一轮按守则低成本补齐 (vendor 或 FETCHCONTENT_SOURCE_DIR) 后重验，本轮不提前关闭测试 |
| 2 | HMDFS 符号链接与共享库 SONAME 风险 | CMake 安装共享库产生版本符号链接 | 默认 `shared=False` 静态交付；`shared=True` 时沿用上游 CMake 安装语义，真机验证后再评估 |
| 3 | 真机 cmake.configure 在 compiler check 失败，HMBS 诊断 readonly_tmp (/tmp 只读，preflight.sh 报 can't create /tmp/sh*.tmp) | 主配方 generate()/build() 未设置可写 TMPDIR，clang 临时文件默认走只读 /tmp | 新增 `_ensure_writable_tmpdir()`：优先复用 HMBS 注入的 TMPDIR/TMP/TEMP（真实文件写入探测），不可写时回退到 build_folder/_tmp 私有目录；generate()/build() 首行调用并同步 TMPDIR/TMP/TEMP。test_package 同步为同探测逻辑。不改上游测试口径 |
| 4 | 上轮 TMPDIR 生效（日志出现 using writable TMPDIR）但仍在 CMakeLists.txt:14 project() 报 CMAKE_C_COMPILER=/data/service/hnp/bin/clang 失败 | Conan CMakeToolchain 在 os=OHOS 时映射出 CMake 无平台模块的 system 名（ML-0035，System is unknown to cmake），裸 clang 编译器自检无法通过；与 clamav-libunrar 同指纹 | 改用已验证 ohos.toolchain+裸 cmake：generate() 不再生成 CMakeToolchain/CMakeDeps，主配方自发现 ohos.toolchain.cmake 并裸 cmake 配置/构建/安装（SPGLIB_* 映射不变，ctest 口径不变），test_package 改为直接 clang 编译+运行（消除第二个 CMake project 失败点），保留 TMPDIR 探测与 .so 重签容错 |
| 5 | ohos.toolchain 路线在预检机直接 exit 6：Invalid configuration: ohos.toolchain.cmake not found（SDK glob 无命中，OHOS_NDK_HOME/user_toolchain 未注入） | 上轮假设的 /data/service/hnp/ohos-sdk.org SDK 布局在此 worker 不存在，硬依赖导致连 cmake.configure 都未执行 | 回到 HMBS/CI 支持的 CMakeToolchain 路线：恢复 CMakeToolchain/CMakeDeps 与 CMake helper；把探测到的可写目录同时经 buildenv_info.define 写入 conanbuild.sh（上轮仅 os.environ，日志可见但未进入 self.run 子进程环境，应是传导机制问题）；test_package 保留直接 clang 编译 |
| 6 | 前三轮 TMPDIR 传导修复后日志已打印 using writable TMPDIR，但仍在 CMakeLists.txt:14 project() 失败：System is unknown to cmake + CMAKE_C_COMPILER=/data/service/hnp/bin/clang error | 根因不在临时目录：Conan 把 OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，vanilla CMake 4.4.3 无 Platform/HarmonyOS 模块，编译器 ABI 自检无法完成；TMPDIR 只是伴随的 readonly_tmp 警告 | 新路线 E092/zxc(0.9.1) precedent：generate() 经 tc.variables 强制 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64，让 CMake 加载 Platform/Linux.cmake；OHOS clang 仍由 profile 的 compiler_executables 提供；保留 TMPDIR 探测与 buildenv 传导，不改测试口径 |
| 7 | Round-6 Linux override still failed at project(): compiler identification unknown for /data/service/hnp/bin/clang (same fingerprint, 2nd repeat) | Prior hypothesis (missing Platform/HarmonyOS module) invalid: log shows TMPDIR already writable yet check still fails; worker is native OHOS/aarch64 (build==host, ADAPTATION_GUIDE section 2), so forcing SYSTEM_NAME=Linux flips CMake into cross mode while compiler stays native OHOS clang -> check mismatch. Different route required, not same override | Remove SYSTEM_NAME/PROCESSOR override (native auto-detect); keep TMPDIR probe+buildenv; add CMAKE_POLICY_VERSION_MINIMUM=3.5 for CMake 4.4.3 floor (E187, independent); fix ctest cwd via _locate_ctest_dir() probing build/Release for CTestTestfile (cmake_layout out-of-source) |
| 11 | 上轮build期-D覆盖仍失败：错误仍指向/data/.../clang且失败行在cmake.configure(variables=overrides)（toolchain内FORCE使-D无法 displacement） | 工具链set(...CACHE...FORCE)优先于命令行-D；且C候选为空时未复用已验证CXX | 新路线：build()内实测后直接改写conan_toolchain.cmake内set行并同步CC/CXX，无可用C时复用可用CXX；configure恢复无参调用 |
| 10 | 上轮isfile-only裸名回退仍失败：日志仅pin CXX而C沿用/data/.../clang，sanity仍FileNotFoundError（文件存在但execve失败，isfile无法识别） | isfile只能证存在不能证可执行，且generate期无buildenv，裸名clang仍可能命中坏路径 | 新路线：generate期零编译器pin，build()内buildenv生效后--version实测conf/CC/PATH候选，经cmake.configure(variables)做-D覆盖（优先于toolchain缓存） |
| 9 | Rounds 9-11 generate-time --version probing + harmonybrew/SDK glob + sibling/bindir scan + CXX-as-C still left C dangling (5th-cycle: same family 3x) | generate() runs before profile buildenv PATH/LD_LIBRARY_PATH, so probe rejects SDK clang and accepts host clang++; which() empty at generate time but valid at build time | New route: zero-probe fallback (isfile only, no subprocess/which/glob, no worker paths); dangling conf -> bare clang/clang++ resolved at build time via buildenv PATH; test_package drops SDK/harmonybrew globs likewise |
| 8 | Round-7 no-override failed with explicit "System is unknown to cmake, create Platform/HarmonyOS..." + same compiler unknown (3rd repeat, proves both halves needed) | Round-7 native hypothesis invalid: vanilla CMake 4.4.3 has no Platform/HarmonyOS module, so no override cannot configure; round-6 variables-only Linux override removed the System-unknown line but left compiler check failing -> link stage of try-compile is the remaining breakage, plus variables precedence may be weaker than cache | Combined route: cache_variables SYSTEM_NAME=Linux + PROCESSOR=aarch64 (CACHE precedence) with TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY (compile-only check, no link/sysroot needed); keep TMPDIR/POLICY/ctest-dir; add read-only _log_compiler_sanity ($CC --version) to separate cannot-execute vs cannot-link in next log |
| 13 | 真机 configure 期 FetchContent git clone googletest 超时（3 次重试，SSL EOF / 443 连不上）致 configure 中断 | 上游 test/CMakeLists.txt 写死 GIT_REPOSITORY github.com googletest v1.15.2；预检机无 GitHub 直连，但 gh-proxy 文件下载可达 | conandata third_party 预下载官方 v1.15.2 tarball（gh-proxy 优先、官方回退，同 sha256），source() 解到 third_party/gtest，generate() 注入 FETCHCONTENT_SOURCE_DIR_GTEST 避开 git（沿用 wasmedge 0.17.1 已验证路线）；不关测试、不改上游源码 |
| 12 | 本轮预检 ctest 明明跑了 45 个用例 (36/45 Passed, Total Test time 18.73s) 但 HMBS_UPSTREAM_TEST_RESULT 报 discovered 0, 触发 "ctest reported zero tests" | 旧 _parse_ctest_summary 只认单空格英文汇总行，未去 ANSI 色码，空白符写死；汇总行若含双空格/色码即 miss，且无 fallback 计数，导致有执行也判 0 | 健壮化解析：去 ANSI + \s+ 宽松匹配汇总行；miss 时回退计数外层 N/M Test #K Passed/Failed 行 (内层 build-and-test 无此前缀，不会 double-count)，再回退任意 Test #N 行；ctest 子进程显式注入可写 TMPDIR/TMP/TEMP 并打 raw bytes 日志。上游 audit：test/CMakeLists 仅用 build-tree 目录，未硬编码 /tmp，仅做 temp-root 重定向，不删测试 |

## 源码修改

无补丁 (patches 为空)。未修改任何上游文件；
POSIX 兼容，无需 `__OHOS__` 平台宏。

## 依赖版本

无 (C 核心零外部运行时依赖；测试期 GTest 由上游 FetchContent
按需获取，不进入配方 requires)。

## 验证结果

```bash
# 真机预检 (HMBS 后台执行，本轮等待调度)
# conan create archives/s/spglib/2.7.0 --user=ohpcd --channel=stable
#   -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 预期: ctest 全绿 + HMBS_UPSTREAM_TEST_RESULT + HMBS_TEST_PACKAGE_RESULT 双标记
```

## 注意事项

- Fortran/Python/OpenMP 均为可选组件，本次仅交付 C 主库
  (`Spglib::symspg`)；需要时后续版本再评估。
- `url` 字段填上游仓库地址 (代码风格门禁要求，非空)。
- 本轮不 commit、不 push、不建 PR；验证由 HMBS 后台执行。

**编译结束**: 2026-09-15
**最终状态**: built (待真机 HMBS 全部门禁)
