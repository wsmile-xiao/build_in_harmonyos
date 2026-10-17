# libproperties 1.1.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（aarch64-linux-ohos，`ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 编译步骤

`conan create <包目录> -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64> --build=missing --user=ohpcd --channel=stable`：

1. `source()`：`get()` 下载 `https://github.com/tinyhubs/libproperties/archive/1.1.2.zip`
   （sha256 `9ee3903648f8de6c9e2d71fd778721844cc9881dcc2afe2c66cdb2d1cb86b39a`），`strip_root=True`。
2. `generate()`：`CMakeToolchain` 注入 `BUILD_SHARED_LIBS=ON`、`LIBPROPERTIES_TEST=ON`、
   `LIBPROPERTIES_INSTALL=ON`、`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,`（见下表 2）。
3. `build()`：`cmake.configure()` + `cmake.build()` + **上游 ctest**——
   `ctest --test-dir <build folder> --output-on-failure`，跑之前把构建树目录前置进
   `LD_LIBRARY_PATH`（见下表 1）。上游 `CMakeLists.txt` 用
   `file(GLOB test/*.properties)` 逐文件 `add_test()`，注册 **2** 个用例。
4. `package()`：`cmake.install()` → `lib/libproperties.so{,.1,.1.1.2}` + `include/properties.h`
   + `lib/cmake/libproperties-config*.cmake`（8 个文件）。
5. `test_package/test()`：`self.run(<绝对路径二进制>, env="conanrun")` 直跑 2 个消费者测试
   （`cmake.test()` 会被 W3 L0d 判 `stub_test_method`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ctest` 两个用例全红：`Error loading shared library libproperties.so.1` | 设备与 CI 的 CMake 都把 `CMAKE_SYSTEM_NAME` 认作 `HarmonyOS`，但安装里没有 `Modules/Platform/HarmonyOS.cmake`（configure 首屏即打 `System is unknown to cmake, create: Platform/HarmonyOS`），rpath 相关链接标志因此从未定义——实测 `CMAKE_BUILD_RPATH=<dir>` 设了也**静默无效**，测试可执行文件 `readelf -d` 无 RPATH/RUNPATH 条目 | 配方 `build()` 在调 ctest 前把构建树目录前置进 `LD_LIBRARY_PATH`；**不改**上游 `CMakeLists.txt`、不加补丁 |
| 2 | 共享库缺 `DT_SONAME`，安装树只有裸 `libproperties.so`（无 `.so.1`/`.so.1.1.2`），W3 会报 `L5a: … 缺少 DT_SONAME` | 同一个缺失的平台模块使 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 未定义：lld 收不到 `-Wl,-soname`，且 CMake 在此状态下**连版本化文件名都不生成** | `generate()` 注入 `tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"`（producer 侧链接期修复，不改 ELF、不重签）。修复后 `libproperties.so → libproperties.so.1 → libproperties.so.1.1.2`、`DT_SONAME = libproperties.so.1`、消费者 `DT_NEEDED` 记裸名 |
| 3 | `conan-verify` L4 报 `NX=disabled`（3 个 .so 各 1 条警告） | 工具的 NX 判据取 `GNU_STACK` 之后 200 字符并要求其中不含字母 `E`，而实际窗口里紧跟 `NOTE` 段名（含 `E`）⇒ 确定性误报 | 人工 `readelf -lW` 复核：`GNU_STACK … RW`（无 `E`）⇒ NX 生效；`GNU_RELRO` + `FLAGS BIND_NOW` ⇒ full RELRO；`DYN` + AArch64。逐条读数见 `reports/conan-verify-supplement.md`（工具判据属框架层，不在本 PR 修） |
| 4 | `conan-verify` L2 `⏭️ SKIP（无 bin/ 目录）` | 纯库包没有 `--version` 可执行产物，探针无目标 | 按「跳过即非证据」处置：人工补测（消费者测试真跑 + 安装树清单与 `package_info()` 对账）写入 `reports/conan-verify-supplement.md` |

## 源码修改

**无补丁**：`patches/` 为空，`conandata.yml` 的 `patches: {}`。上表 1、2 两处平台适配全部内联在
`conanfile.py` 的 `generate()` / `build()`，上游 `*.c`/`*.h`、`CMakeLists.txt`、`test/` 夹具
逐字节未动，`test/*.properties` 与 `*.j.expect` 原样使用。

## 依赖版本

- 运行时依赖：**无**（`requirements()` 为空；产物 `readelf -d` 的 `NEEDED` 仅 `libc.so`）
- Conan 构建依赖：**无**（不需要 `tool_requires`，cmake/clang/make 设备与 CI 均自带）
- 设备工具：cmake 4.1.2、clang 15.0.4、GNU Make 4.4.1、Conan 2.29.1

## 验证结果

```bash
# ① 上游测试（conanfile.py build() 末尾的 ctest，干净轮日志逐字）
1/2 Test #1: 1.properties .....................   Passed    0.03 sec
2/2 Test #2: 2.properties .....................   Passed    0.02 sec
100% tests passed, 0 tests failed out of 2

# ② 消费者测试（test_package/test()，conanrun 环境）
test_libproperties_api: OK (3 entries parsed, greeting matched)
test_libproperties_soname: OK (libproperties.so.1 resolved by bare soname)

# ③ conan-verify 干净轮门禁
G0 PASS / G1 PASS / G2 PASS / G3 PASS / G4 PASS / L4 PASS / L5 PASS / L2 SKIP(人工补测)
```

被验证 SHA、日志字节数与 sha256、逐条人工补测读数见 `reports/test-report.md` 与
`reports/conan-verify-supplement.md`（两者由 `.gitignore` 排除在提交面之外）。

## 注意事项

- 上游 `CMakeLists.txt` 的 `install(EXPORT … DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/${PROJECTNAME}")`
  里 `${PROJECTNAME}` 未定义（应为 `${PROJECT_NAME}`），配置文件因此落在 `lib/cmake/` 而不是
  `lib/cmake/libproperties/`；两条路径都在 CMake 的 config 搜索面内，且 Conan CMakeDeps 以
  生成器目录优先，实测 `find_package(libproperties)` 正常。属上游小瑕疵，**未修改上游文件**。
- 上游 `build.sh` 的 shebang 是 `#!/usr/bin/bash` 且用 bash 语法（`[[`）；本配方直接驱动 CMake、
  不调用 `build.sh`，因此不涉及设备缺 `/bin/bash` 的缺口。
- `libproperties_test` 是 `add_executable` 出来的测试执行器，**没有** `install()` 规则，不在
  `package()` 交付面内（G4 清单只有 `lib/` 与 `include/`）。
- 上游 tag 双形态 `1.1.2` 与 `libproperties-1.1.2` 在 2026-09-25 均实测存在
  （`git ls-remote --tags`），`conandata.yml` 采用 tag `1.1.2` 的 codeload zip。
