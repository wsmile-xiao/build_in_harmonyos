# DRAFT-hdrhistogram-c-0.11.8-sysroot-lib-inject-test-recovery — OHOS 下用 sysroot 系统库注入恢复 find_package 门控的上游测试入口

**路径**: B（知识库扩展）
**来源任务**: hdrhistogram-c-0.11.8-r01-pc6-1-20260906T152320Z
**触发事件**: 首次适配 HdrHistogram_c 0.11.8，上游 hdr_histogram_log_test（25 例）因 conan 工具链找不到 sysroot 内的 zlib 而保持 uninstantiated

## 问题

HdrHistogram_c 0.11.8 的 `test/CMakeLists.txt` 仅在 `HDR_LOG_ENABLED`（=`ZLIB_FOUND`）为真时注册 `hdr_histogram_log_test`（25 个 mu_run_test 用例）。OHOS sysroot（`/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot`）自带 `zlib.h` 与 `libz.so`，但 conan 生成的 `conan_toolchain.cmake` 只把 `CMAKE_PREFIX_PATH` 指向 generators 目录，不会搜索 sysroot —— 因此 `find_package(ZLIB)` 失败：

```
-- Could NOT find ZLIB (missing: ZLIB_LIBRARY ZLIB_INCLUDE_DIR)
```

上游因此把 `HDR_LOG_ENABLED` 置为 FALSE，`hdr_histogram_log_test` 不实例化；连带 `src/CMakeLists.txt` 选用 `hdr_histogram_log_no_op.c`（log 组件退化为 no-op）。

既有解决方式（assimp/aevol 等 29 个归档配方）是从 **conan 依赖包**（`self.dependencies["zlib"].package_folder`）注入 ZLIB 路径；kpackage 草稿是**消费者侧** find_dependency 修复。二者都不覆盖"库直接消费 **sysroot 系统库**、且目的是**恢复被门控的上游测试入口**"的场景。

## 根因

1. OHOS 交叉编译下 conan CMakeToolchain 不把 sysroot 加入 `CMAKE_FIND_ROOT_PATH`/搜索路径，Module 模式 `find_package(ZLIB)` 找不到 sysroot 系统库；
2. 上游用 `find_package(ZLIB)` 同时门控 log 实现（`hdr_histogram_log.c`）与 log 测试（`hdr_histogram_log_test`），zlib 找不到 → log 组件与 25 例测试一起消失；
3. 只改 `HDR_LOG_REQUIRED=ON` 不够——`find_package` 仍搜不到 sysroot，且上游对 `HDR_LOG_REQUIRED=ON` 且找不到 zlib 会直接 `SEND_ERROR`。

## 方案

在配方 `generate()` 中按 `settings.os == "OHOS"` 注入 sysroot 系统库路径：

```python
import glob
sysroots = glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot")
if self.settings.os == "OHOS" and sysroots:
    sysroot = sorted(sysroots)[-1]
    tc.variables["HDR_LOG_REQUIRED"] = "ON"
    tc.variables["ZLIB_INCLUDE_DIR"] = sysroot + "/usr/include"
    tc.variables["ZLIB_LIBRARY"] = sysroot + "/usr/lib/aarch64-linux-ohos/libz.so"
    tc.variables["ZLIB_LIBRARY_RELEASE"] = tc.variables["ZLIB_LIBRARY"]
else:
    tc.variables["HDR_LOG_REQUIRED"] = "OFF"
```

要点：
- 用 glob 定位 SDK 路径而非硬编码版本号，版本升级仍可用；
- 同时注入 `ZLIB_LIBRARY_RELEASE`（CMake Module 模式 Release 配置会读它）；
- 非 OHOS 平台保持 `HDR_LOG_REQUIRED=OFF`，不改变其他平台行为；
- 不新增 conan 依赖、不引入制品仓包，直接消费系统库（zlib 为 OHOS 系统基础库，运行期由系统提供）。

配套恢复同类被门控入口：
- 上游 `if(UNIX)` 守卫在 OHOS 不成立导致 `hdr_histogram_atomic_concurrency_test`（1 例）未注册 → 补丁扩展为 `if(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`；
- 双口径台账验证：`source_declared_total=64`，`configured_executable_total=64`，`executed_passed_total=64/64（100%）`，`uninstantiated=0`。

## 验证

- `conan create . --version=0.11.8 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...`：构建成功，`hdr_histogram_log_test`、`hdr_histogram_atomic_concurrency_test` 均被构建并安装；
- ctest（本地 OHOS 工具链构建）：5/5 测试通过，`100% tests passed, 0 tests failed out of 5`；
- log_test 直接运行 `ALL TESTS PASSED / Tests run: 25`，concurrency 测试 `Tests run: 1`；
- SONAME 补全 + 重签（patchelf → llvm-objcopy 剥旧签名 → binary-sign-tool 自签）不受影响，L5 门禁通过；
- 新增 HarmonyOS 专项测试 `test_ohos_platform`（时间 API/原子并发/累积与百分位），随 test_package 运行通过。

## 适用边界 / 反例

- 适用：OHOS 目标上、库直接消费 sysroot 自带系统库（zlib 等）、且该库用 `find_package` 门控可选组件/测试的 C/C++ 配方；
- 反例：需要版本锁定或必须走制品仓依赖的库，应改用 `self.requires("zlib/1.3.1")` + 依赖包路径注入（assimp 模式），不得混用两种来源；
- 反例：非 OHOS 平台保持原配置，注入代码必须按 `settings.os` 守卫；
- 边界：若上游 `HDR_LOG_REQUIRED=ON` 且找不到 zlib 会 `SEND_ERROR`，因此"注入成功"与"恢复测试"绑定，注入失败时应回退 `HDR_LOG_REQUIRED=OFF` 而非硬失败。

## 查重差异

- `similar_to`: E323（依赖包 CMAKE_PREFIX_PATH 注入）、E438（CMAKE_FIND_ROOT_PATH_MODE_PACKAGE）、DRAFT-kpackage-karchive-619（消费者侧 find_dependency 修复）
- `conflicts_with`: 依赖包注入方式（本方案用 sysroot 系统库，无 conan 依赖）
- 新增差异：生产者侧 **sysroot 系统库**注入恢复 **find_package 门控的上游测试入口**，配合双口径台账（64/64）与 OHOS 专项测试，既有条目均未覆盖该完整链路。
