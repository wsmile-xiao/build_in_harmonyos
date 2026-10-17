# sonivox 3.6.16 测试报告

> **项目**: sonivox 3.6.16（EAS 波表 MIDI 合成器，AOSP platform_external_sonivox 的 CMake 移植）
> **测试日期**: 2026-09-21
> **测试环境**: HarmonyOS PC / HongMeng Kernel 1.12.0 aarch64（HarmonyOS 6.1.0.117），OHOS SDK clang 15.0.4
> **测试类型**: 官方测试套件（GoogleTest/ctest）+ 消费者 API 回归（test_package）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 52 | 100% |
| 通过 (PASS) | 52 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

- 上游官方测试：**33/33 PASS（100%）**（`test/SonivoxTest.cpp`，ctest 注册 33 项）
- 消费者测试：**19/19 PASS（100%）**（`test_package/test.c`，conan create 实跑）

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**：上游测试套件在真机原样运行全部通过；EAS 合成器核心功能
（配置契约 / SMF 解析 / 离线渲染 / 定位 / 暂停恢复 / DLS 音色库加载）全部可用；
CLI `sonivoxrender` 真机渲染输出有效 PCM。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无缺陷级问题 | — | — |
| `sonivoxrender -v/-h` 退出码为 1（上游行为） | CI L2 smoke 判 warn（non-blocking） | 🟢 |

### 2.3 可用功能清单

```
✅ EAS_Init / EAS_Config / EAS_Shutdown：库生命周期与配置查询（3.6.16.0, 44100Hz, 2ch, 64 voices）
✅ EAS_OpenFile / EAS_Prepare / EAS_ParseMetaData：SMF MIDI 解析（格式 0/1 等）
✅ EAS_Render：内嵌波表采样离线渲染（实测峰值 32768，96.3% 样本非零）
✅ EAS_Locate / EAS_GetLocation：毫秒级定位
✅ EAS_Pause / EAS_Resume：暂停/恢复状态机
✅ EAS_LoadDLSCollection：外部 DLS 音色库加载（Airfont_340.dls，81MB）
✅ sonivoxrender CLI：MIDI → raw PCM（stdout），支持 reverb/chorus/gain 参数
```

### 2.4 已知限制

1. 上游 CLI `--version`/`--help` 返回退出码 1（上游实现如此），CI L2 判 non-blocking warn，
   本适配不修改上游行为。
2. 交付构建 `BUILD_TESTING=OFF`：上游测试 configure 期需联网下载 81MB DLS + GoogleTest，
   为保证 `conan create` 自包含，上游测试在适配验证阶段以独立构建树运行（本报告数据来源）。
3. 库不提供 MIDI 输入/音频输出设备接口（上游设计，需使用方自行接入）。

---

## 三、测试详情

### 3.1 上游官方测试（33/33 PASS，`ctest --output-on-failure`）

| 测试组 | 实例数 | 覆盖功能 | 结果 |
|--------|--------|----------|------|
| SonivoxTestAll/SonivoxTest.DecodeTest | 11 | 全曲解码渲染、reverb 参数、播放长度断言（midi_a 2000ms / midi8sec 8002ms / midi_cs 2000ms / midi_gs 2000ms / ants 17233ms） | ✅ 全部 PASS |
| SonivoxTestAll/SonivoxTest.SeekTest | 11 | 定位到 0 / 中点 / 末尾，及越界定位必须失败 | ✅ 全部 PASS |
| SonivoxTestAll/SonivoxTest.DecodePauseResumeTest | 11 | 定位中点 → 渲染 → 暂停（位置不变）→ 恢复（位置前进、状态 PLAY） | ✅ 全部 PASS |

参数组：5 组使用内嵌音色库（""），6 组加载 `soundfont.dls`
（含 1 组 ants.mid DLS 重复参数）；DLS 按上游 CMake 校验
`size=81362584`、`MD5=40c0cd4ad29ae411a8fc3d6681002a2b` 后使用。

### 3.2 消费者测试（19/19 PASS，`test_package/test.c`）

| # | 断言 | 结果 |
|---|------|------|
| 1 | EAS_Config 返回非空配置 | ✅ PASS |
| 2 | 库版本 == 3.6.16.0 | ✅ PASS |
| 3 | 采样率 == 44100 Hz | ✅ PASS |
| 4 | 输出声道 == 2 | ✅ PASS |
| 5 | mixBufferSize > 0 | ✅ PASS |
| 6 | EAS_Init 成功且句柄非空 | ✅ PASS |
| 7 | EAS_SetVolume 成功 | ✅ PASS |
| 8 | 生成的 SMF 文件可打开 | ✅ PASS |
| 9 | EAS_OpenFile 接受生成的 SMF | ✅ PASS |
| 10 | EAS_Prepare 成功 | ✅ PASS |
| 11 | EAS_ParseMetaData 播放时长 > 0 | ✅ PASS |
| 12 | 播放时长约为 500ms（450–600ms） | ✅ PASS |
| 13 | PCM 缓冲区分配成功 | ✅ PASS |
| 14 | 渲染循环无 API 错误 | ✅ PASS |
| 15 | 渲染帧数 ≥ 500ms 音频 | ✅ PASS |
| 16 | 渲染 PCM 非静音（峰值 > 0） | ✅ PASS |
| 17 | EAS_CloseFile 成功 | ✅ PASS |
| 18 | EAS_Shutdown 成功 | ✅ PASS |
| 19 | 负例：坏文件被 EAS_OpenFile 拒绝（`No parser recognized the requested file`） | ✅ PASS |

### 3.3 失败的测试

无。

### 3.4 跳过的测试

无。

---

## 四、关键问题分析

### 问题1: 上游测试的 configure 期联网依赖

**现象**：
```
Downloading DLS file for testing to /.../TEMP/soundfont.dls
file(DOWNLOAD "http://www.ronimusic.com/sf2/Airfont_340.dls" ...)
FetchContent_Declare(googletest GIT_REPOSITORY "https://github.com/google/googletest.git")
```

**根因分析**：
上游 CMakeLists.txt 在 `BUILD_TESTING=ON` 时（默认）强制下载 81MB DLS 音色库
并在找不到系统 GTest 时 FetchContent 拉取 GoogleTest；这两步使 `conan create`
依赖外网且体积巨大，不适合作为交付构建路径。

**解决方案**：
交付 conanfile 固定 `BUILD_TESTING=OFF`（自包含构建）；验证阶段另建测试构建树：
GTest 使用制品仓已有 `gtest/1.17.0`（本地缓存，OHOS 构建），DLS 由 `$TEMP/soundfont.dls`
提供（上游 size+MD5 校验通过），上游测试源码与用例**零修改**运行。

---

## 五、测试环境

```
uname -m: aarch64
OS: HarmonyOS 6.1.0.117（HAD-W32/W24），Kernel 1.12
编译器: clang version 15.0.4（OHOS SDK 26.0.0.18）
CMake: 4.4.3
Conan: 2.29.1（OHOS 适配版）
Profile: ohos-aarch64-device（os=OHOS 6.0 / arch=armv8 / clang 15 / libc++ / cppstd=17 / Release）
GTest: 1.17.0（制品仓缓存二进制）
DLS: Airfont_340.dls（81362584 bytes, MD5 40c0cd4ad29ae411a8fc3d6681002a2b）
```

证据文件：
- `reports/conan-create.log`（conan create 完整日志，含 test_package 执行）
- `reports/conan-verify-report.md`（G0-G4 判定）
- `reports/test-report.md`（本报告）

---

*报告生成时间: 2026-09-21*
