# rhvoice 1.14.0 适配笔记

## 编译环境

- 构建系统: scons（上游 1.14.0 由 SCons 驱动；树内 `CMakeLists.txt` 只服务于 sanitizer 构建）
- 编译日期: 2026-10-10
- 编译器: clang / clang++（OHOS SDK 26.0.0.18，目标 aarch64-unknown-linux-ohos）
- Conan: 2.29.1，profile `ci/conan/profiles/ohos-aarch64`（host == build）
- 语言预检: 主体 C++（R47 口径：`src/` 主体 + 根构建脚本，`android/` 子树与 Gradle 包装不计主体）
- 状态: built

## 编译步骤

1. `source()` 取 codeload 归档（tag `1.14.0`，sha256 `36029c06…5801e2b9`），应用 `patches/0001-sconstruct-allow-construction-variable-override.patch`。
2. 同一函数内解包 `data_sources`（English 语言数据 + dasha-eng 语音数据）到 `data/languages/<name>`、`data/voices/<name>`，随后 `_drop_empty_data_placeholders()` 清掉归档里 data/ 子模块留下的空占位目录。
3. `generate()` 用 pip 把 scons 4.10.0 私有安装到 build 目录下的 `_scons_env`，通过 `PYTHONPATH` 暴露（制品仓无 scons 配方，dxx-rebirth 同款策略）。
4. `build()`: `python3 -m SCons -j<N> audio_libs="" enable_shared=1 dev=0 CPPPATH="<boost include>"`
5. `package()`: `python3 -m SCons install DESTDIR=<package_folder> prefix=/usr`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Checking whether the C compiler works... no`，随后的子进程挂在 `/system/bin/sh` | SCons 不读环境变量里的 `CC`/`CXX`（默认取 `gcc`）；且它用 `posix_spawn` 直接执行构造变量 `SHELL` 里的 `sh`，不搜 PATH——沙盒里默认 shell 不可用 | 补丁允许 `RHVOICE_SCONS_<NAME>` 覆盖任意构造变量；配方把 `CC`/`CXX`/`AR`/`RANLIB`/`SHELL` 从 Conan toolchain 注入（R33：不依赖裸 shell 环境变量） |
| 2 | `patch_ng` 报 `patch stream is incomplete!` / `no patch data found!` | `patch_ng` 不接受自定义补丁前言；同时 hunk 头行数必须与实际 body 完全一致 | 补丁改用标准 git 格式（`diff --git`/`---`/`+++`/`@@`），并逐行核对 hunk 计数 |
| 3 | `FileNotFoundError: …/data/languages/Albanian/language.info` | 发布 tarball 内 `data/*` 子模块为空目录，但 `data/SConscript` 仍会遍历每个目录并读 `<type>.info` | `_drop_empty_data_placeholders()` 在 `source()` 末尾删除空数据目录 |
| 4 | 测试报 `RHVoice_new_tts_engine() returned null` | `src/lib/lib.cpp:174` 强制 `voices.empty()` 抛 `No voices`：C API 至少需要 1 个语音数据 | 包内自带 1 语言 + 1 语音（English + dasha-eng） |
| 5 | 引擎构造抛 `no_languages` | `src/core/engine.cpp:79/104`：传了 `data_path` 但没有语言数据即抛错 | 语言数据与语音数据必须成对安装；消费者测试按包内实际安装目录探测 `config_path`/`data_path` |
| 6 | 语音仓 tarball 疑似不可复现（同一仓库多次下载哈希不同） | 早前探测混用了 `refs/heads/main` 与固定 commit 两种 URL：codeload 对分支是动态打包，对固定 commit 才稳定 | 只用固定 commit 的 codeload URL，并双次下载比对（English 与 dasha-eng 均两次一致） |
| 7 | `Checking for pkg-config... no` | CI 干净环境无 pkg-config，SConstruct 只用它探测可选音频后端 | 无害：`audio_libs=""` 已关闭所有音频后端 |
| 8 | `make: jobserver mkfifo: …/GMfifo…: Operation not permitted` | 沙盒不允许在默认 TMPDIR 建 FIFO | 配方把 `TMPDIR`/`TMP`/`TEMP` 指向 build 目录下的私有 tmp（无害报错，构建继续） |

## 源码修改

`patches/0001-sconstruct-allow-construction-variable-override.patch`（标准 git 格式，+6 行）：
在 `SConstruct` 的 `setup()` 之后，把环境里所有 `RHVOICE_SCONS_<NAME>` 变量注入 `base_env`，
使调用方可以覆盖 `CC`/`CXX`/`AR`/`RANLIB`/`SHELL` 等构造变量。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.91.0.1.3 | 发布 tarball 内 `external/libs/boost` 子模块为空，改用制品仓 boost 头文件，`CPPPATH` 指向其 include |
| scons | 4.10.0 | `generate()` 内 pip 私装到 build 目录（制品仓无该配方），不进入最终包 |
| 语言数据 | RHVoice/English@8a2ea34d | 上游独立数据仓（git submodule），sha256 `426536cb…a0af426` |
| 语音数据 | RHVoice/dasha-eng@3115c266 | CC BY-SA 4.0 语音，sha256 `2b4d763e…69fb8e239` |

数据仓只用**固定 commit** 的 codeload URL；语音数据里的 `voice.info` 由上游自带（`name=Dasha-Eng`），
配方仅在归档不含 `voice.info` 时用 `fields` 生成。非自由许可的语音（如 CC BY-NC-ND 的 Lyubov）不打包。

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# => rc=0，Package '86e8b7c94f8539adfd55978de161e65f75d8660e' created
# 关键输出：
#   PASS: RHVoice_new_tts_engine() returns an engine
#     voices: 1
#     voice 0: name=Dasha-Eng language=en
#   synthesized 44520 samples at 24000 Hz
#   all checks passed
# 完整日志: ~/tmp/rhv-build.log（905524 B，sha256 044032100b995f63b5194c8fbd9c54b56de562230c4ba232c64538c2764ece42）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `usr/lib/libRHVoice.so.5.1.0`（+ `.so`/`.so.5` 符号链接） | C API |
| `usr/lib/libRHVoice_core.so.10.0.0`（+ `libRHVoice_audio.so.2.0.0`） | 引擎内核 / 回调音频后端 |
| `usr/bin/RHVoice-test` | 上游合成工具（音频后端关闭时不构建 `RHVoice-client`） |
| `usr/include/RHVoice.h`、`RHVoice_common.h` | 公开 C 头文件 |
| `usr/share/RHVoice/languages/English`（19 文件）、`usr/share/RHVoice/voices/dasha-eng`（8 文件） | 内置语言与语音数据 |
| `usr/etc/RHVoice/RHVoice.conf` | 引擎配置 |

## 注意事项

- 上游无自动化测试套件（`ci.yml` 只跑 `scons -j2`），测试依托 `test_package`（12 项断言 + `RHVoice-test --help`）。
- **适配完整性（R40，需人工确认）**：OHOS 无系统音频服务，`audio_libs=""` 关闭了 pulse/libao/portaudio/speech-dispatcher 后端，
  库改由 C API 回调路径交付样本（`libRHVoice_audio`）。本次验证覆盖到"回调按帧交付样本正确"（44520 样本 / 24000 Hz），
  端侧把回调样本接入 `AudioRenderer` 的真机链路属消费方集成范围，列为后续验证计划；配方内无平台宏、无 stub 分支。
- 库以动态库形式交付（非系统同名库），依赖链由 Conan 管理；`runenv_info` 已把 `usr/bin` 加入 PATH。
- 消费者若自行指定 `data_path`，必须同时提供至少一个语音的语言数据，否则引擎抛 `no_languages`。
---

**编译结束**: 2026-10-11 10:41
**最终状态**: built
