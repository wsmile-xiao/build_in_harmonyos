# qrq 0.3.5 适配笔记

## 编译环境
- 构建系统: makefile（手写 Makefile，无 configure / autotools）
- 编译日期: 2026-10-10
- 编译器: clang（OHOS SDK 15.0.4）
- 目标: aarch64-linux-ohos
- 状态: built

## 编译步骤

qrq 上游使用手写 Makefile，音频后端由 `USE_CA` / `USE_PA` / `USE_WIN32` 变量
选择（默认 `USE_PA=YES`）。鸿蒙适配新增 `USE_OHOS` 分支：

```bash
# 依赖：ncurses/6.5（Conan 制品仓，静态 libncursesw.a）
make USE_PA=NO USE_OHOS=YES CC=clang -j1
```

产物：`qrq`（可执行文件）。数据文件（callbase.qcb / english.qcb / cwops.qcb /
qrqrc / toplist）与 man page 由 Makefile 的 install 规则安装到
`share/qrq/` 与 `share/man/man1/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 HarmonyOS 音频后端 | 仅支持 OSS / PulseAudio / CoreAudio / WinMM | 新增 `ohosaudio.c`（原生 OHAudio 后端，经 `export_sources` 交付，见下），Makefile 增加 `USE_OHOS` 分支（patch 0001），qrq.c 增加 `OHOS_AUDIO` 分支（patch 0002） |
| 2 | OHAudio 只有回调模型 | 无 OSS 那样的 `write()` 直接写接口 | 后端缓存 `write_audio()` 推入的采样，在 `close_audio()` 中 `OH_AudioRenderer_Start()`，回调内按帧取出并回填静音 |
| 3 | `make install` 失败 | 鸿蒙无 `/usr/bin/install`（`INSTALL ?= install` 找不到命令） | 配方 `package()` 直接用 `copy()` 收集产物，不调用 `make install` |
| 4 | Makefile 默认后端为 PulseAudio | `USE_PA=YES` | 编译时显式传 `USE_PA=NO USE_OHOS=YES` |

## 源码修改

补丁（`patches/`，仅修改既有文件）：

- `0001-Makefile.patch`：新增 `USE_OHOS` 变量与后端分支（`-D OHOS_AUDIO -pthread`，
  链接 `-lpthread -lohaudio -lncursesw`，`OBJECTS=qrq.o ohosaudio.o`）。
- `0002-qrq.c.patch`：新增 `#ifdef OHOS_AUDIO` 分支引用 `ohosaudio.h`，
  并让 `add_to_buf(buffer, 88200)` 的 OSS 专用路径不作用于 OHOS 后端。

新增源码（**非补丁**）：`compat/ohosaudio.c` / `compat/ohosaudio.h` 通过
conanfile.py 的 `export_sources()` 传递，`build()` 时复制到源码目录。之所以不
写成 new-file 补丁，是因为 E254：toybox 的 `patch --dry-run` 对 new-file 补丁会
真实创建目标文件，污染 `.orig` 基线，使 refresh-patch 生成带 `a/` 前缀、conan
无法应用的补丁。

## 依赖版本

- ncurses/6.5（静态 `libncursesw.a`，提供 `-lncursesw`）
- 系统库：`libohaudio.so`（OHOS SDK sysroot，`aarch64-linux-ohos`）

## 验证结果

```bash
# conan create 通过
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# smoke test（无自动化上游测试）
qrq -h                # 打印 "qrq v0.3.5 ..." 并退出 0
readelf -d qrq        # NEEDED: libohaudio.so（证明 OHAudio 后端已链接）
```

## 上游测试

上游**没有自动化测试**：源码树无 `tests/` 目录，`make check` 无对应目标。
可用的真实入口是 `qrq -h`（打印帮助/版本后退出）。因此适配另新增一个
鸿蒙特有测试（`test_package`），验证 OHAudio 后端被链接且原生 OHAudio
渲染器可用。

## 注意事项

- 运行时需要 terminfo 数据库（ncurses）；`qrq -h` 在 `initscr()` 之前退出，
  不需要 terminfo，但进入 TUI 需要可用的 TERM 条目。
- 音频输出依赖 HarmonyOS 系统音频服务，无需 PulseAudio 守护进程。

### 对话 #1 [2026-10-10]

- 问题: 上游仅支持 OSS / PulseAudio / CoreAudio / WinMM 音频后端，鸿蒙无 `/dev/dsp` 也无 PulseAudio 守护进程
- 操作: 新增原生 OHAudio 后端 `ohosaudio.c/.h`，Makefile 增加 `USE_OHOS` 分支，qrq.c 增加 `OHOS_AUDIO` 分支
- 结果: 编译链接系统 `libohaudio`，`readelf -d` 确认 NEEDED

### 对话 #2 [2026-10-10]

- 问题: OHAudio 只提供回调（pull）模型，而 qrq 一次性生成整段波形后调用 `write_audio()`/`close_audio()`
- 操作: 后端缓存采样，`close_audio()` 中启动 `OH_AudioRenderer` 并在回调内按帧供给与静音回填，等待全部采样被消费
- 结果: 设备上真实运行 `OHOS_AUDIO_PASS: callbacks=6 frames=24576`

### 对话 #3 [2026-10-10]

- 问题: 上游 `make install` 依赖 `/usr/bin/install`，鸿蒙缺失
- 操作: 配方 `package()` 改用 `copy()` 收集 bin/share 产物
- 结果: conan 包布局正确（bin/qrq、share/qrq、share/man/man1）
---

**编译结束**: 2026-10-10 13:56
**最终状态**: built
