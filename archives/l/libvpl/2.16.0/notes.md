# libvpl 2.16.0 适配笔记

## 编译环境

- 构建系统: cmake (CMake >= 3.13; 设备 CMake 4.1.2 + Ninja 1.13.1)
- 编译日期: 2026-09-15
- 目标平台: OpenHarmony / HarmonyOS PC, aarch64 (conan profile `ci/conan/profiles/ohos-aarch64`, os=OHOS, arch=armv8)
- 编译器: OHOS SDK clang 15.0.4 (`/data/service/hnp/bin/clang`, target `aarch64-unknown-linux-ohos`), libc++
- Conan: 2.29.1 (OHOS 适配版), host/build profile 同为 `ohos-aarch64`
- 拓扑: 无第三方依赖 (仅 host 侧 CMake 工具链)；上游测试的 googletest 随源码 vendored

## 编译步骤

配方即 CI 的唯一构建输入，标准 `conan create` 即可；关键是 `generate()` 中显式设置系统名：

```python
tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"         # 见下节，必须
tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
tc.variables["BUILD_SHARED_LIBS"] = True           # 上游默认 ON
tc.variables["BUILD_TESTS"] = "ON"                 # 跑上游 ctest
tc.variables["INSTALL_DEV"] = "ON"                 # 头文件 + VPLConfig.cmake + vpl.pc
tc.variables["INSTALL_LIB"] = "ON"
tc.variables["INSTALL_EXAMPLES"] = "OFF"           # 示例需要真实 Intel 硬件
tc.variables["BUILD_EXAMPLES"] = "OFF"
```

本地复核（不使用 Conan 的等价 CMake 直跑）：

```bash
CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ \
cmake -S libvpl-2.16.0 -B build -G Ninja \
  -DCMAKE_SYSTEM_NAME=OHOS -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTS=ON -DINSTALL_EXAMPLES=OFF -DBUILD_EXAMPLES=OFF
cmake --build build -j 2
cd build && ONEVPL_SEARCH_PATH=$PWD ctest --output-on-failure -j 2
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原生 configure 后 `libvpl.so` 只导出 7 个符号（MFXLoad/MFXUnload/MFXCreateConfig/MFXSetConfigFilterProperty/MFXEnumImplementations/MFXCreateSession/MFXDispReleaseImplDescription），`MFXInit`/`MFXInitEx`/`MFXQueryVersion` 等 1.x API（52 个符号）全部缺失，且共享库无 `DT_SONAME` | CMake 没有 `Platform/HarmonyOS.cmake`；设备 `uname -s` 返回 `HarmonyOS`，Conan 对 `os=OHOS` 的默认系统名也是 `HarmonyOS`，两者都没有平台文件 → `CMAKE_SYSTEM_NAME` 为空或不可识别、`UNIX` 未定义。`libvpl/CMakeLists.txt` 的 `if(UNIX)` 分支被整段跳过：`src/linux/mfxloader.cpp` 不进入构建图，`MFX_MODULES_DIR` 未定义，`find_package(Threads)` 与 `-pthread` 链接也一并跳过；`DT_SONAME` 同时丢失，因为 `CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG` 由 `Platform/Linux.cmake` 定义。**两处易误归因**（均已实测排除）：①`-Wl,--version-script=src/linux/libvpl.map` 位于 `if(WIN32)` 的 `else()` 分支，破损配置下**仍然生效** —— 破损产物仍带 `LIBVPL_2.0`/`LIBVPL_2.1` 版本节点，只是只覆盖存活的那 7 个符号；②`${CMAKE_DL_LIBS}` 的链接在 `if(UNIX)` **之外**（无条件），`CMAKE_DL_LIBS` 由 `Platform/GNU.cmake` 兜底，破损配置下 `build.ninja` 仍有 `LINK_LIBRARIES = -ldl`（正确配置多出的是 `-pthread`） | `generate()` 中 `tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"`（SDK 随带 `Modules/Platform/OHOS.cmake`，其内容为 `include(Platform/Linux)`；用平台真名而非伪装成 Linux，仓库内同口径先例：`archives/d/demumble`、`archives/d/dbus`）。`UNIX=1` 后 `mfxloader.cpp` 入库、`DT_SONAME` 生成、version script 覆盖全部 59 个符号。无需源码补丁 |
| 2 | 直接 `python3 scripts/ohc-run.py init-build ... --url=https://github.com/...` 报 `CERTIFICATE_VERIFY_FAILED` | 设备 Python (OpenSSL) 期望的 CA 路径 `/etc/ssl/cert.pem` 不存在；`init_build.py` 的下载分支直接调用 `urllib.request.urlopen`，未走同文件里已有的免校验回退 `_urlopen` | 进程内注入已存在的 CA 包：`SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem`（不改全局环境）。已记入容器层 feedback |
| 3 | `init-build` 生成的 `manifest.yaml`/`notes.md` 是 autotools 分支的模板占位（软件名字段未替换、构建系统错标为 `autotools`、状态字段被写成发布态），且创建了已废弃的 `packaging/` | 模板按 autotools 分支生成，且未识别 CMake 项目 | 按 `knowledge/ARCHIVE-SPEC.md` v3.0 重写版本级 `manifest.yaml`/`notes.md`，补齐软件级 `manifest.yaml`/`README.md`，删除 `packaging/`（v3.0 明文废弃） |
| 4 | 分账时 ctest 汇总显示 `100% tests passed ... out of 1014`，无法区分 PASS 与 SKIP | ctest 把 GTEST_SKIP 计为 passed | 以 `ctest --output-junit` 的 `skipped=` 属性或 gtest 单进程输出分账：707 PASS / 307 SKIP / 9 DISABLED |

## 源码修改

无。本版本不改上游源码、不引入任何补丁：平台差异完全由 `CMAKE_SYSTEM_NAME=OHOS` 解决，`patches/` 目录不创建。

## 依赖版本

- 无 Conan 运行时/构建依赖（`preflight_check.sh libvpl/2.16.0` → 预检通过，无依赖需要检查）
- 上游测试的 googletest 为源码内 vendored 副本（`libvpl/test/ext/googletest`，212 个文件），不引入 `test_requires`

## 验证结果

```bash
# conanfile.py build() 内执行（与 CI 同源）
ctest -N                                  # Total Tests: 1023
ctest --output-on-failure -j 2            # 100% tests passed, 0 tests failed out of 1014
./vpl-tests                               # [==========] 1014 tests from 26 test suites ran
                                          # [  PASSED  ] 707 tests
                                          # [  SKIPPED ] 307 tests
```

计数口径（R51 三步法）：

| 项 | 值 | 口径 |
|---|---|---|
| 上游源码声明数 | 860 | `TEST`/`TEST_F` 字面宏（`libvpl/test/unit/src/*.cpp`） |
| 上游框架注册数 **N** | 1023 | `ctest -N`（`gtest_discover_tests` 构建期枚举） |
| 本次实际运行数 N′ | 1014 | gtest `[==========] ... ran`；= 1023 − 9 DISABLED |
| PASS | 707 | |
| SKIP | 307 | GPU / CPU 运行时 / legacy 加速器 / `vpl-inspect` 相关，OHOS 无 Intel 运行时 |
| FAIL | 0 | |
| DISABLED（未运行） | 9 | 上游 `DISABLED_` 前缀，ctest 不计入 "out of" |

差额 163（1023 − 860）的归因（口径：框架注册数 − 源码关键字命中数）：
- **+174** 来自两个**生成宏**（字面关键字统计看不到调用点）：
  - `legacycpp-session-test.cpp` 的 `TEST_CUSTOM` **40 个调用点**，该文件被 `legacycpp-session-test-1x.cpp` / `-2x.cpp` 各 `#include` 一次（`LEGACY_TEST_VER=1/2`）→ 注册 **80** 项（ctest 侧 `LegacycppCreateSession1x` / `2x` 各 40）；
  - `dispatcher_stub_propquery.cpp` 的 `TEST_PROPQUERY_VALID`(18) / `_VALID_NOFN`(18) / `_INVALID`(11) 共 **47 个调用点**，每个宏体含 **2** 个 `TEST(...)` → 注册 **94** 项（该 suite 注册总数 111 = 94 生成 + 17 字面）；
- **−11** 来自"关键字命中但不产生独立注册项"的部分（逐项可查）：
  - 6 处位于 `TEST_PROPQUERY_*` 宏定义体内的 `TEST(...)`（`dispatcher_stub_propquery.cpp:505/509/516/521/528/533`）；
  - 2 处位于 `dispatcher_stub_stringapi.cpp:841/871` 的 `TEST_F(StringAPITest, Set{test_name})` **宏模板体**内；
  - 2 处被 `/* … */` 注释掉（`dispatcher_stub_stringapi.cpp` 第 275 行起的注释块内两条 `TEST(Dispatcher_Stub_StringAPI, …)`，该 suite 在 `--gtest_list_tests` 的 29 个 suite 中确实不存在）；
  - 1 处位于 Windows 专用分支 `dispatcher_gpu.cpp:247` `#if defined(_WIN32) || defined(_WIN64)` 内（`D3D9CanCreateSession`）。

即 **860 + 174 − 11 = 1023**。（另：3 处 `DISABLED_` 前缀项**仍注册**，只是 ctest 侧会剥掉 `DISABLED_` 前缀，故属已注册字面项。）

以最大口径 1023 申报，不发生少报。

## 交付物

`conan create` 产出的包内容（`libvpl/2.16.0`，shared）：

| 路径 | 说明 |
|------|------|
| `lib/libvpl.so.2.16`、`lib/libvpl.so.2`、`lib/libvpl.so` | 派发库（SONAME `libvpl.so.2`，version script `LIBVPL_2.0`/`LIBVPL_2.1`） |
| `include/vpl/*.h` | oneVPL 2.16 API 头（19 个 + `preview/`） |
| `lib/cmake/vpl/VPLConfig.cmake`、`VPLConfigVersion.cmake` | 上游 CMake 包配置（`VPL::dispatcher`） |
| `lib/pkgconfig/vpl.pc` | pkg-config（可重定位） |
| `etc/vpl/vars.sh` | 上游开发环境脚本（按自身路径推导，可重定位） |
| `licenses/LICENSE`、`licenses/third-party-programs.txt` | 许可证 |
| `share/vpl/licensing/*` | 上游安装的许可证副本 |

## 注意事项

- 派发库本身不包含任何编解码实现：它按 `ONEVPL_SEARCH_PATH` → 自身所在目录 → `MFX_MODULES_DIR`（编译期 `CMAKE_INSTALL_FULL_LIBDIR`）→ 系统目录的顺序 `dlopen` 运行时（`libmfx-gen`/`libmfxhw64`/`libmfxsw64`）。OHOS 上不存在 Intel 运行时，因此运行期只能枚举到"无实现"（`MFX_ERR_NOT_FOUND` / `MFX_ERR_UNSUPPORTED`），这是平台事实而非适配缺陷。
- 上游 ctest 默认只跑 stub 实现（`main.cpp`：无自定义参数时 `g_bDispInclStub = true`）；stub 运行时由构建树内的 `vplstubrt*` 提供，`gtest_discover_tests` 通过 `ONEVPL_SEARCH_PATH=$<TARGET_FILE_DIR:vplstubrt>` 注入。`conanfile.py` 的单进程复核同样显式设置该变量。
- `-workDir <dir>` 对本套件无影响（实测 707/307 与默认一致）。
- `ctest` 把 SKIP 计入 passed：只看 ctest 汇总会把 307 项跳过误判为通过，必须用 `--output-junit` 或 gtest 原始输出分账。
- 9 项 `DISABLED_` 为上游显式禁用（`legacycpp-session-test.cpp` 中的 `DISABLED_` suite），不属适配引入。
