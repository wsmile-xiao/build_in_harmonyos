# openal/1.24.1 测试报告（OpenHarmony PC aarch64）

- 执行方式：`conan create` 内置 test_package（os=OHOS / armv8 / clang 15 / libc++ / cppstd=17）
- 日志：`reports/conan-create.log`（工作区留存，不入库）
- 结论：**全部通过**

## 统计

| 指标 | 数量 | 说明 |
|------|------|------|
| 总测试数 | 34 | 上游移植用例 1 + 消费者端到端断言 33 |
| 通过 PASS | 34 | 33/33 断言 + 上游用例 1/1 |
| 失败 FAIL | 0 | |
| 跳过 SKIP | 0 | |

## 1) 上游官方测试（层 1，R51 三步法）

- 清点：上游仅 `tests/example.t.cpp`（`ExampleTest.Basic`，GTest；经 FetchContent 拉 gtest，
  `ALSOFT_TESTS` 默认 OFF）。除此之外无任何测试套件/ctest 注册项（`grep -rn ctest tests/` 为空）。
- 运行：交叉构建不拉取 gtest（FetchContent 需联网），故将该用例去依赖移植为
  `test_package/upstream_basic.cpp`（保留原断言体：声明 AL API 类型并检查错误状态），
  随 conan create 在真机执行。
- 实测结果：

```text
PASS: upstream ExampleTest.Basic API surface compiles and links
INFO: ALuint=4 bytes, ALfloat=4 bytes, ALenum=4 bytes
INFO: alGetError() before any context = 0xa004
```

## 2) 消费者端到端用例（test_openal.c，33 断言）

`test_openal_consumer`（C，静态 libopenal 消费者）：

- **A) null 后端（18 断言）**：`ALSOFT_DRIVERS=null` → `alcOpenDevice` →
  `alcCreateContext`/`alcMakeContextCurrent` → 校验 `alGetString(AL_VERSION)` 含
  **"1.24.1"**（证明被测对象就是本包）、`AL_VENDOR="OpenAL Community"`、
  `AL_RENDERER="OpenAL Soft"` → `alGenBuffers`/`alBufferData(MONO16)`/`alGenSources`/
  `alSourcei(AL_BUFFER)` → `AL_PLAYING`→`AL_STOPPED` 状态机 → 负路径
  （非法属性返回 `AL_INVALID_ENUM`）→ 资源释放与 `alcCloseDevice`。
- **B) loopback 后端（15 断言）**：`alcLoopbackOpenDeviceSOFT` + `ALC_SOFT_loopback`/
  `ALC_SOFT_HRTF` 扩展声明 → 8 kHz / mono / short 属性上下文（`alcIsRenderFormatSupportedSOFT`
  确认格式）→ 上传 220 Hz 正弦（0.5 FS）→ `alcRenderSamplesSOFT` 实渲染 960 样本：
  peak=16383（恰为 0.5 FS）、非静音（948/960 非零）、零交叉 54（= 2×220 Hz×0.12 s，
  与源频率一致）→ 第二渲染块仍有效 → 设备关闭。

```text
TOTAL: 33 / PASS: 33 / FAIL: 0
```

## 已知限制

- 无真实音频设备可用：外部后端（ALSA/PulseAudio/Oboe/OpenSL 等）在 OHOS 上无对应系统服务，
  配方按设计全部关闭，仅保留上游无条件编译的 Null + loopback 后端（与仓内 openal/1.25.2 口径一致）。
- 上游测试仅 1 个编译型 GTest 用例，已移植执行；未运行 gtest 原框架（FetchContent 需联网）。
