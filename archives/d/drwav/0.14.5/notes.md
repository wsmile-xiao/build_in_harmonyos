# drwav 0.14.5 适配笔记

## 编译环境
- 构建系统: header-only（单头文件库，无 configure/make 步骤；上游仓库 dr_libs 提供 CMakeLists 仅用于构建测试）
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，/data/service/hnp/bin/clang）
- 状态: built（conan-verify 通过后由 finish 定稿）

## 库简介

drwav（dr_wav，mackron dr_libs 家族）是单文件 WAV 音频读写库：整个库就是
单个 `dr_wav.h`，消费者 `#include "dr_wav/dr_wav.h"` 并在恰好一个翻译单元中
定义 `DR_WAV_IMPLEMENTATION` 编译进实现。不产出 lib/ 制品，无运行时依赖。

- 上游仓库：https://github.com/mackron/dr_libs
- 官方标签：`wav-0.14.5`（dr_libs 仓库内以 `wav-<版本>` 标签发布）
- License：Unlicense OR MIT-0（双许可）
- 运行时依赖：无（仅标准 C 库）

## 上游源码核验

| 项目 | 值 |
|------|-----|
| 官方仓库 | https://github.com/mackron/dr_libs |
| 官方标签 | `wav-0.14.5` |
| 官方 tag archive URL | https://codeload.github.com/mackron/dr_libs/tar.gz/refs/tags/wav-0.14.5 |
| 官方归档格式 | tar.gz（220,910 字节） |
| 官方归档 SHA-256 | `6559786208ec001f05fd380fbc2d68043130cef36235aa8092ae75574c36e66f` |
| 归档内 dr_wav.h SHA-256 | `c69816d0e0ac6cab3df8bf2f42df451d4531c2bfa34f7d7a69e959e6ed399038`（9060 行） |
| 版本自检宏 | `DRWAV_VERSION_MAJOR 0` / `DRWAV_VERSION_MINOR 14` / `DRWAV_VERSION_REVISION 5`（0.14.5） |

## header-only 判定

drwav 是 single-header 库，按 header-only 打包（对齐同仓 dr_wav 0.13.17、
dr_mp3 0.7.2 先例）：

- `package_type = header-library`
- `no_copy_source = True`
- `package_id()` 调用 `self.info.clear()` 清理为 header-only
- 只安装 `include/drwav/drwav.h`（含 LICENSE），不伪造 lib/ 制品

## 上游官方测试逐入口台账（源：官方 wav-0.14.5 tag archive）

可复现枚举规则：`find tests/wav/ -type f`（在官方 tag archive 根目录执行）→ 共 7 个文件，
另加 tests/common/dr_common.c 公共模块。分类：**3 个独立可执行入口（含 main）** +
**2 个 .cpp wrapper（1 行 `#include` 对应 .c，无独立 main）** + **1 个调试沙箱**
（官方 CMakeLists 明示 "not intended to be run as a test"）+ **2 个公共模块**
（wav_common.c、dr_common.c，无 main）= 7 + 1。

CMakeLists（`DR_LIBS_BUILD_TESTS=ON`，找到 sndfile.h 时）注册 5 个测试可执行：
wav_decoding、wav_decoding_cpp、wav_encoding、wav_playback、wav_playback_cpp；
wav_debugging 仅加入 IDE 集成、不注册为测试。

| # | 相对路径 tests/wav/ | 分类 | main | 尝试命令（工作目录 `…/dr_libs-wav-0.14.5/tests/`） | 退出码 | 结果 | 首条 stderr / 阻塞归属 | 绝对日志（SHA-256） |
|---|---|---|---|---|---|---|---|---|
| 01 | wav_encoding.c | 独立入口 | 有（写 WAV） | `clang -std=c89 -O2 -Wall -o bin/wav_encoding wav/wav_encoding.c -lm` + `./bin/wav_encoding enc_output.wav` | 0 / 0 | ✅ 编译+运行 PASS（生成 352,844B WAV） | 无 | compile `97e24e3d…` / run log（stdout） |
| 02 | wav_decoding.c | 独立入口 | 有（基准对比） | `clang -std=c89 -O2 -Wall -Isndfile.h头目录 -o bin/wav_decoding wav/wav_decoding.c -lm` + `./bin/wav_decoding` | 0 / 255 | ⛔ 编译 OK；运行被外部阻塞 | 编译 OK（复用 conan libsndfile/1.2.2 头文件）；运行 `Failed to initialize libsndfile API.`——OHOS 制品仓 libsndfile 仅静态 .a 无运行期 .so，且官方 tag 归档 `tests/testvectors/wav/tests` 无测试数据（仅 .gitkeep）→ 外部依赖/上游数据缺失 | compile `eb21c452…` / run `d1687033…` |
| 03 | wav_playback.c | 独立入口 | 有（音频播放） | `clang -std=c89 -O2 -Wall -I../../external/miniaudio -o bin/wav_playback wav/wav_playback.c -lm` | 1 | ⛔ 不可编译（本轮） | `fatal error: '../../../miniaudio/miniaudio.h' file not found`（官方 tag 归档未含 miniaudio 子模块 checkout）；运行另需真实音频设备 → 外部依赖 + 设备 | compile `9479e21a…` |
| 04 | wav_debugging.cpp | 调试沙箱 | 有（return 0） | `clang++ -std=c++11 -O2 -Wall -o bin/wav_debugging wav/wav_debugging.cpp -lm` | 1 | ⛔ 不计入独立用例 | 官方 CMakeLists 明示 "The debugging sandbox is not intended to be run as a test"；其 include wav_common.c 亦需 sndfile.h | compile `b0192f76…` |
| 05 | wav_decoding.cpp | wrapper | 无独立 main（1 行 include .c） | `clang++ -std=c++11 -O2 -Wall -o bin/wav_decoding_cpp wav/wav_decoding.cpp -lm` | — | 复用 02 结论，不重复计数 | 无独立 main | — |
| 06 | wav_playback.cpp | wrapper | 无独立 main（1 行 include .c） | `clang++ -std=c++11 -O2 -Wall -o bin/wav_playback_cpp wav/wav_playback.cpp -lm` | — | 复用 03 结论，不重复计数 | 无独立 main | — |
| 07 | wav_common.c | 公共模块 | 无 main | 不作为独立目标编译；被 wav_decoding.c/wav_debugging.cpp 包含 | — | 非入口（不重复计数） | 其 sndfile.h 依赖已计入 02/04 | 见 02/04 日志 |

复用关系：05/06 分别包装 02/03，无独立 main（源码仅 1 行 `#include`），执行证据全部
来自被包装入口；不重复计数。04 为官方明示非测试的调试沙箱，不计入独立用例。

恢复条件：02 需发布 libsndfile 运行期共享库（OHOS）并提供官方 testvectors 数据；
03 需 checkout miniaudio 子模块 + 音频硬件。

依赖状态复查（规则：首次跳过与最终回报前各查询一次）：
- 首次（2026-09-06T22:2x）：`conan list libsndfile/* -r=ohpcd` → libsndfile/1.2.2 已发布；
  `conan download libsndfile/1.2.2 --only-recipe` 成功；`conan install libsndfile/1.2.2 -pr ohos-aarch64`
  → 仅静态 libsndfile.a（无 .so）；`conan list miniaudio/*` → miniaudio/0.11.25 已发布，
  但 `conan install miniaudio/0.11.25` 报配方 broken（Conan 2.0 不兼容）。
- 最终回报前将再查询一次并记录（见最终回报）。

## 双口径测试统计

| 口径 | 数值 |
|------|------|
| `source_declared_total`（官方 tag 源码独立入口） | 3（wav_encoding.c、wav_decoding.c、wav_playback.c） |
| `configured_executable_total`（实际实例化/注册独立可执行） | 3（与源码声明一致；cpp wrapper 为打包入口不独立计数） |
| `executed_passed_total` | 1（wav_encoding） |
| 失败/阻塞 | 2（wav_decoding 外部运行阻塞、wav_playback 外部编译阻塞） |
| 未运行/未实例化 | 0（全部 3 个独立入口均已尝试编译/运行） |

全量通过率：**1/3 = 33.3%**（通过数/发现总数；未运行、不可运行、硬阻塞计入分母不计为通过）。
实际执行集合通过率：已实际运行 1 项且通过 → 1/1 = 100%（另列，不替代全量通过率）。

## 门禁结论

- conan create / conan-verify / W3 本地 CI：见 Step 3 finish 执行记录与 reports/。
- W5 知识图谱：drwav 未引入新错误模式（header-only 零补丁）；知识查重见知识候选台账。
- 零 patch：未修改任何 drwav 源码。

## 交付物

header-only 包：include/drwav/drwav.h + licenses/LICENSE。无 lib/、无 bin/ 制品。

---

**编译开始**: 2026-09-06 22:15
**最终状态**: built
---

**编译结束**: 2026-09-06 23:04
**最终状态**: built
