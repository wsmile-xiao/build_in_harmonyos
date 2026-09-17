# 测试报告 — libpano13 2.9.23

## 测试统计

| 统计项 | 数值 |
|--------|------|
| 总测试数 | 11 |
| 通过 PASS | 11 |
| 失败 FAIL | 0 |
| 跳过 SKIP | 0 |

（上游 ctest 8 项 + 自研 test_package 3 项断言，全部通过）

## 1. 上游测试（ctest，OHOS 真机实测）

上游 2.9.23 采用 CMake 构建，tests/ 下通过 `ctest` 注册 8 个测试用例，
全部由 `tests/panoAutomateTest.pl` + `tests/panoAutomatePSDtest.pl` 驱动，
经 `tools/` 下 PTtiff2psd/PTmender 等命令处理 `simpleStitch`/`simpleTiff16`/
`simpleTiff2psd` 测试图像并与 `reference/` 结果比对。

| 测试 | 结果 |
|------|------|
| simpleStitch | ✅ Passed |
| simpleTiff16-16bit-1-layer | ✅ Passed |
| simpleTiff16-16bit-2-layers | ✅ Passed |
| simpleTiff2psd-1-layer | ✅ Passed |
| simpleTiff2psd-2-layers | ✅ Passed |
| simpleTiff2psd-1-layer-uncropped | ✅ Passed |
| simpleTiff2psd-2-layers-uncropped | ✅ Passed |
| simpleTiff2psd-1-layer-cropped | ✅ Passed |

**上游测试通过率：8/8（100%）**

> 注：上游 CMake 生成的 tools 二进制以斜杠相对 NEEDED（`../libpano13.so`）引用
> 共享库，动态加载器按进程 cwd 解析（不受 LD_LIBRARY_PATH 控制）。本地实测时
> 在 build/tests/ 下放置指向 `../libpano13.so` 的符号链接后全部用例通过。
> 该问题与既有知识 `DRAFT-libjpeg-turbo-3.0.4-slash-relative-NEEDED-ctest-loading`
> 属同一根因，conan 配方通过 `-Wl,-rpath-link` + 安装期共享库部署天然规避，
> 不构成功能缺陷。

## 2. 自研 test_package 测试（conan create 自动执行）

`test_package/test.c` 编译为消费者可执行程序，实质调用 libpano13 公开 API 并含 3 项硬断言：

| 断言 | 说明 | 结果 |
|------|------|------|
| `panoProjectionFormatCount() > 0` | 库注册投影格式数量（实测 = 22） | ✅ |
| `queryFOVLimits(1, ...) == 1` | 投影视场角查询返回成功（上游源码 0=失败/1=成功，实测 rc=1） | ✅ |
| `lims[0] > 0 && lims[1] > 0` | 视场角结果合理（实测 maxhfov=360.0 maxvfov=179.0） | ✅ |

另有 `PT_setProgressFcn`/`PT_setInfoDlgFcn` + `Progress(0,...)` 回调链路验证（调用不崩溃即通过）。

**新增测试通过率：3/3（100%）**

## 3. 验证环境

- 平台：OpenHarmony PC (arm64, OHOS 6.0)
- 工具链：clang 15.0.4（OHOS NDK ohos.toolchain.cmake）
- Conan：2.29.1（OHOS 适配版）
- 构建命令：`conan create . --version=2.9.23 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
