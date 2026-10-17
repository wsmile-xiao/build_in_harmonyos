# libexadrums 0.7.0 测试报告（W3 本地 CI 模拟）

- **测试时间**：2026-09-19
- **测试方式**：`conan create archives/l/libexadrums/0.7.0`（触发 `test_package` 编译 + 运行）
- **构建配置**：Release（CI profile `ohos-aarch64`，含 `-DNDEBUG`）
- **目标架构**：OHOS aarch64（clang 15 / libc++）
- **结论**：通过

## 测试项

`test_package/test.cpp` 对 libexadrums 公共 API 做真实调用，共 **4 条断言**（覆盖 3 个方面）。
断言使用自定义 `CHECK` 宏（非 `<cassert>`）：CI 走 `build_type=Release`（`-DNDEBUG`），
`assert()` 会被预处理剔除、测试退化为恒返回 0 的空壳；`CHECK` 在 Debug/Release 下均真实执行，
失败时打印文件行号并以非零码退出：

| # | 断言 | 期望 | 实际 | 结果 |
|---|------|------|------|------|
| 1 | `GetVersion()` | `== "0.7.0"` | `libexadrums version = 0.7.0` | PASS |
| 2 | `GetDevices(SND_PCM_STREAM_PLAYBACK)` 非空 | 返回 ≥1 个设备 | `ALSA playback devices = 1` | PASS |
| 3 | `AlsaParameters` XML 往返 — device | `== "default"` | `round-trip device = default ...` | PASS |
| 4 | `AlsaParameters` XML 往返 — sampleRate | `== 44100` | `... sampleRate = 44100` | PASS |

运行输出末尾：`ALL libexadrums OHOS stub tests passed`，进程退出码 0。

## 构建产物

- `libexadrums.so.2.0.0`（动态库，内嵌 ALSA 静态桩 libasound.a）
- 头文件：`include/libexadrums/`、`include/alsa/`

## 说明

- 上游 libeXaDrums 无正式测试套件（无 `make check` 目标），适配后补全 consumer 端冒烟测试作为鸿蒙特有测试。
- 测试在 OHOS 设备（aarch64）本地原生运行；为解决 framework `CMAKE_SKIP_RPATH` + 传递依赖 libminizip/libtinyxml2 的加载问题，test_package 在运行期显式注入 `LD_LIBRARY_PATH`（覆盖全部依赖 lib 目录）。
- **适配完整性（R40）**：音频后端因 OHOS 无 ALSA 整体桩化为 no-op，本适配为编译级适配；断言覆盖 API 可用性，不覆盖真实音频播放。
