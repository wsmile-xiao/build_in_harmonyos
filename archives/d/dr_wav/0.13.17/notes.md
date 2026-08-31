# dr_wav 0.13.17 适配笔记 — R03 归档来源修正闭环

> 本文件随 R03 更新：将 R02 的 raw 单文件来源替换为官方 tag archive 并重验。

## 库简介

dr_wav 是 David Reid（mackron）dr_libs 家族的单文件（single-header）WAV 音频
读写库。整个库就是单个 `dr_wav.h`，消费者 `#include "dr_wav/dr_wav.h"` 并在
**恰好一个**翻译单元中定义 `DR_WAV_IMPLEMENTATION` 编译进实现。

- 上游仓库：https://github.com/mackron/dr_libs
- 版本标签：`wav-0.13.17`（dr_wav 在 dr_libs 仓库内以 `wav-<版本>` 标签发布）
- License：Unlicense OR MIT-0（双许可，任选其一）
- 运行时依赖：无（仅标准 C 库）

## 上游源码核验（R03 归档来源修正）

| 项目 | 值 |
|------|-----|
| 官方仓库 | https://github.com/mackron/dr_libs |
| 官方标签 | `wav-0.13.17` |
| 标签 commit | `660795b2834aebb2217c9849d668b6e4bd4ef810`（"dr_wav: Version 0.13.17"，2024-12-16T23:51:21Z） |
| **官方 tag archive URL** | `https://codeload.github.com/mackron/dr_libs/tar.gz/refs/tags/wav-0.13.17` |
| 官方归档格式 | tar.gz（gzip，518,811 字节） |
| **官方归档 SHA-256** | `6a06744f9e961e8417f1ce9ee0d884cc8f00108d1a08845ced7f8696847ff8ec` |
| 归档内 dr_wav.h SHA-256 | `9948d5343a879d4644693b2832005e9fbbb7581929223a1775cbde559a835388`（与 R02 单文件核验一致） |
| 归档内 dr_wav.h 大小 | 352,642 字节（8,829 行） |
| 版本自检宏 | `DRWAV_VERSION_MAJOR 0` / `DRWAV_VERSION_MINOR 13` / `DRWAV_VERSION_REVISION 17`（0.13.17） |

> R03 修正说明：R02 使用 raw 单文件 URL（`raw.githubusercontent.com/.../dr_wav.h`）
> 不满足"官方 tag archive"来源规则，已替换为 codeload.github.com 官方 tag
> archive。归档经 SHA-256 校验，且归档内 dr_wav.h 与 R02 已核验的单文件哈希
> 完全一致，证明内容未变、仅来源形式合规化。

## header-only 判定

dr_wav 是 **single-header** 库：整个库就是 `dr_wav.h`，上游 README 推荐用法为
直接把头文件加入源码树。本包按 header-only 打包（对齐 miniaudio 0.11.25 先例）：

- `package_type = header-library`
- `no_copy_source = True`
- `package_id()` 调用 `self.info.clear()` 清理为 header-only
- **不伪造 lib/ 制品**：只安装 `include/dr_wav/dr_wav.h`

## 安装布局

本包安装到 `include/dr_wav/dr_wav.h`。消费者 CMake：

```cmake
find_package(dr_wav REQUIRED)
target_include_directories(app PRIVATE ${dr_wav_INCLUDE_DIRS})
# 并在恰好一个 .c 文件中 #define DR_WAV_IMPLEMENTATION 后 #include "dr_wav/dr_wav.h"
```

## 上游官方测试逐入口台账（R04 校正版，源：官方 wav-0.13.17 tag archive）

可复现枚举规则：`find tests/wav/ -type f`（在官方便签 clone 根目录执行）→ 共 **8 个文件**。
1-1 分类：**4 个独立可执行入口**（含 `main`）+ **3 个 .cpp wrapper**（1 行 `#include` 对应 .c，无独立 main）+ **1 个公共模块**（dr_wav_common.c，无 main，被 decoding 包含）= 8。

| # | 相对路径 tests/wav/ | 分类 | main | 尝试命令（工作目录 `…/dr_libs/tests/`） | 退出码 | 结果 | 首条 stderr / 阻塞归属 | 绝对日志（SHA-256） |
|---|---|---|---|---|---|---|---|---|
| 01 | dr_wav_test_0.c | 独立入口 | 有（空占位） | `clang -std=c89 -O2 -Wall -o …/bin/dr_wav_test_0 dr_wav_test_0.c` + 运行 | 0 / 0 | ✅ 可运行且已运行 PASS | 无 | compile `5e833bae…9b0` / run `d1af45d3…4211` |
| 02 | dr_wav_encoding.c | 独立入口 | 有（写 WAV） | `clang -std=c89 -O2 -Wall -o … dr_wav_encoding.c -lm` + `./dr_wav_encoding r04_enc.wav` | 0 / 0 | ✅ 可运行且已运行 PASS（生成 352,844B WAV） | 无 | compile `5e833bae…9b0` / run `d1af45d3…4211` / 产物 `r04_enc.wav` |
| 03 | dr_wav_test_0.cpp | wrapper | 无独立 main（1 行 include .c） | `clang++ -std=c++11 -O2 -Wall -o … dr_wav_test_0.cpp` + 运行 | 0 / 0 | ✅ 复用 01 证据编译+运行 PASS | 无 | compile `5e833bae…9b0` / run `d1af45d3…4211` |
| 04 | dr_wav_decoding.c | 独立入口 | 有（基准对比） | `clang -std=c89 -O2 -Wall -o … dr_wav_decoding.c -lm` | 1 | ⛔ 不可运行（本轮） | `fatal error: 'sndfile.h' file not found`（dr_wav_common.c:3）；需 libsndfile + `tests/testvectors/wav/tests`（官方 archive 内不存在）→ 外部依赖/上游数据缺失 | `3b39c010…1d19` |
| 05 | dr_wav_decoding.cpp | wrapper | 无独立 main（1 行 include .c） | `clang++ -std=c++11 -O2 -Wall -o … dr_wav_decoding.cpp -lm` | 1 | ⛔ 复用 04 阻塞 | 同 04（sndfile.h 缺失）→ 外部依赖/上游数据缺失 | `06f1fe46…cd13` |
| 06 | dr_wav_playback.c | 独立入口 | 有（音频播放） | `clang -std=c89 -O2 -Wall -I../../external/miniaudio -o … dr_wav_playback.c -lm` | 1 | ⛔ 不可运行（本轮） | `fatal error: '../../../miniaudio/miniaudio.h' file not found`（tag archive 未含 submodule checkout）；运行另需真实音频设备 → 外部依赖 + 设备 | `adc7cb31…f3ba` |
| 07 | dr_wav_playback.cpp | wrapper | 无独立 main（1 行 include .c） | `clang++ -std=c++11 -O2 -Wall -I../../external/miniaudio -o … dr_wav_playback.cpp -lm` | 1 | ⛔ 复用 06 阻塞 | 同 06（miniaudio 缺失）→ 外部依赖 + 设备 | `620b5125…eb4` |
| 08 | dr_wav_common.c | 公共模块 | 无 main | 不作为独立目标编译；被 dr_wav_decoding.c 包含 | — | 非入口（不重复计数） | 其 sndfile.h 依赖已计入 04/05 | 见 04/05 日志 |

复用关系：03/05/07 分别包装 01/04/06，无独立 `main`（源码仅 1 行 `#include`），执行证据全部来自被包装入口；不重复计数。
恢复条件：04/05 需提供/发布 libsndfile 与官方 testvectors 数据；06/07 需 checkout miniaudio 子模块 + 音频硬件。
可复算统计（独立入口 4 个）：可运行且已运行 2（test_0、encoding）；不可运行 2（decoding、playback）；未运行（可运行但本轮未跑）0；wrapper/公共模块 4 个不计入独立入口数。

## 门禁结论（R03/R04 复核见 reports/ 与最终回传）

- conan create / conan-verify / W3 本地 CI 模拟：R02 曾通过，R03 来源变更后重验。
- W5 知识图谱：dr_wav 未引入新错误模式/草稿。

## Adapt 阶段待办（后续轮次）

- [ ] submit 就绪项（test-report.md、packaging/、.staging-verified）与 PR — 需远端授权
- [ ] 上游 decoding 入口依赖 libsndfile + testvectors 外部数据（外部阻塞）

## 零 patch

自 R01 起未修改任何 dr_wav 源码，无 patch。
---

**编译结束**: 2026-08-31 08:28
**最终状态**: built
