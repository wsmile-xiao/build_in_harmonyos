# oaml 1.3.4 测试报告（HarmonyOS PC / aarch64）

> 日志留存说明：完整原始日志 `reports/conan-create.log` 随本 PR 提交；
> conan 缓存构建目录 `~/.conan2/p/b/oaml71acba6ec3fdc/`（本地复现路径）。

## 一、上游测试（R51 三步法）

### 1. 清点

| 项 | 结论 |
|---|---|
| `tests/` 目录 | 不存在（63 个上游文件全部清点，见 notes.md） |
| ctest / pytest 注册 | 无 |
| CMake 测试目标 | 仅 `ENABLE_TEST` → `oamlTest`（默认 OFF） |
| 自动化测试用例数 | **0** |

### 2. 可运行性

`oamlTest`（src/test.cpp）为**交互式 demo**：`InitAudioDevice(44100)` 依赖 RtAudio
真实输出设备（OHOS 无 ALSA/Pulse/JACK 后端），随后从 stdin 逐字符读命令直到输入
`q`，**无任何自动化断言**，无头环境不可运行。

**实际执行**：以 `-DENABLE_TEST=ON` 真实编译该入口（conan-create.log 行
`Build oamlTest executable: Yes`，构建目标 `[40/61]~[61/61] oamlTest`，产物
`build-ohos/oamlTest` 存在），证明上游测试入口在 OHOS 工具链下可编译。

### 3. 统计回填（如实申报）

| 指标 | 值 |
|---|---|
| 上游测试命令 | `cmake -DENABLE_TEST=ON ...`（构建入口）+ `./oamlTest`（交互式，无法无头运行） |
| 用例总数 | 0（无自动化用例） |
| 通过 / 失败 / 跳过 | 0 / 0 / 0 |
| 说明 | 上游确无自动化测试；test_package 消费者用例**不替代**上游测试，仅为新增的鸿蒙消费者验证 |

## 二、鸿蒙消费者用例（新增，test_package/test_oaml.cpp）

命令：`./test_oaml`（conan create 的 test() 阶段在本机 OHOS PC 上**真实执行**，
执行环境 conanrun env，二进制与依赖 .so 均已代码签名）

| 指标 | 值 |
|---|---|
| 检查项总数 | 11 |
| 通过 | 11 |
| 失败 | 0 |
| 退出码 | 0 |

逐项断言（原始输出见 reports/conan-create.log）：

```
[PASS] oamlApi::GetVersion returns non-empty string
[PASS] generate tone.wav (2s 44100Hz sine)
[PASS] generate oaml.defs
[PASS] Init(oaml.defs) == OAML_OK
[PASS] GetDefsFile round-trip
[PASS] PlayTrack(music) == OAML_OK
[PASS] MixToBuffer produces real decoded audio (non-silence)
[PASS] IsPlaying() == true while main loop playing
[PASS] IsTrackPlaying(music) == true
[PASS] GetPlayingInfo reports the playing track
[PASS] IsPlaying() == false after StopPlaying
oaml consumer test: 11 checks, 0 failures
```

覆盖面：C++ 消费者路径（Init(defs 解析) → PlayTrack → 真实 WAV 解码 + 混音
（libvorbisfile/libogg/libsoxr 依赖闭包）→ 播放状态查询 → 停止/关停），即游戏引擎
嵌入 oaml 的标准无头用法。

## 三、conan create 证据

- `Package '4e21a73f07229fde6ca591a12d277c4177427632' created`（reports/conan-create.log:397）
- Building from source / Copying sources / 61 处 clang++ 编译调用，错误扫描 0
- 依赖二进制全部从 ohpcd 下载（libogg/1.3.6、libvorbis/1.3.7、libsoxr/0.1.3），无 `--build=missing` 绕过
